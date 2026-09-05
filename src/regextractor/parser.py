from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from .hierarchy import HierarchyStack, is_hierarchy_line, is_toc_line
from .metadata import (
    classify_obligation,
    excerpt,
    extract_action,
    extract_amendment_date,
    extract_entity,
    extract_quantitative,
    ocr_flags,
)
from .models import ClauseNode, PageBlock, SourceInventoryRecord, SourceSpan
from .provenance import printed_pages_for, printed_for_pages

PAGE_MARK = re.compile(r"^<!--\s*PDF_PAGE:(\S+)\s+PRINTED_PAGE:(\S*)\s*-->$")
ENGINE_MARK = re.compile(r"^<!--\s*SOURCE_ENGINE:")
MIXED_NESTED = re.compile(
    r"^(?P<id>\d+[A-Za-z]?(?:\(\d+[A-Za-z]?\)|\([A-Za-z0-9]+\))+)\s*(?P<body>\S.*)?$"
)
DECIMAL_CLAUSE = re.compile(r"^(?P<id>\d+(?:\.\d+){1,4})(?:\s+|$)(?P<body>.*)$")
MAIN_CLAUSE = re.compile(r"^(?P<id>\d{1,4}(?:[A-Z]{1,2})?)\.(?P<body>\s*\S.*)$")
PAREN_CLAUSE = re.compile(
    r"^(?P<id>\((?:[0-9]+[A-Za-z]?|[a-z]|[ivxlcdm]+|[A-Z])\))\s+(?P<body>\S.*)$"
)
FOOTNOTE_MARK = re.compile(
    r"^(?P<id>[\*\u2020\u2021\u00b9\u00b2\u00b3\u2070-\u2079]+|\d{1,3})\s+(?P<body>(?:Inserted|Deleted|Substituted|Replaced|Omitted|Added).+)$",
    re.I,
)
FOOTNOTE_INLINE = re.compile(r"^[\*\u2020\u2021\u00b9\u00b2\u00b3\u2070-\u2079]+\s")
STANDALONE_PAGE = re.compile(r"^\d{1,4}$")
YEARISH = re.compile(r"^(19|20)\d{2}[A-Za-z]?$")
STRUCTURAL_NUM = re.compile(r"^\d{1,3}[A-Za-z]?$")
PRINTED_FOLIO = re.compile(r"^(?:Page\s+)?\d{1,4}\s*$", re.I)


def _is_yearish_identifier(cid: str) -> bool:
    return bool(YEARISH.match(cid))


def _is_structural_main_id(cid: str) -> bool:
    core = cid.split("(")[0]
    return bool(STRUCTURAL_NUM.match(core)) and not _is_yearish_identifier(core)


def _scoped_node_id(hierarchy: List[str], clause_id: str) -> str:
    if hierarchy:
        return " > ".join(list(hierarchy) + [clause_id])
    return clause_id


def _kind_for(cid: str) -> str:
    if re.search(r"\(", cid) and cid[0].isdigit():
        return "mixed_nested_clause"
    if re.match(r"^\d+\.\d+", cid):
        return "decimal_clause"
    if re.match(r"^\(\S+\)$", cid):
        return "parenthetical_clause"
    if re.match(r"^\d+[A-Z]+$", cid):
        return "amendment_clause"
    if cid.startswith("footnote:"):
        return "footnote"
    return "main_clause"


def _parent_of(cid: str) -> Optional[str]:
    mixed = re.match(r"^(?P<head>.+)(\([^()]+\))$", cid)
    if mixed:
        return mixed.group("head")
    dec = re.match(r"^(?P<head>\d+(?:\.\d+)*)\.\d+$", cid)
    if dec:
        return dec.group("head")
    return None


def _normalize_body(prefix: str, body: str) -> str:
    body = body or ""
    if body.startswith(" ") or body.startswith("\t"):
        return f"{prefix}{body}".rstrip()
    if body:
        return f"{prefix}{body}".rstrip()
    return prefix.rstrip()


class ParseResult:
    def __init__(self, nodes: List[ClauseNode], inventory: List[SourceInventoryRecord]):
        self.nodes = nodes
        self.inventory = inventory


def parse_markdown_and_blocks(markdown: str, blocks: List[PageBlock], source_pdf_sha256: str = "") -> List[ClauseNode]:
    return parse_document(markdown, blocks, source_pdf_sha256).nodes


def parse_document(markdown: str, blocks: List[PageBlock], source_pdf_sha256: str = "") -> ParseResult:
    stack = HierarchyStack()
    current = None
    nodes: List[ClauseNode] = []
    inventory: List[SourceInventoryRecord] = []
    current_pdf_page = None
    current_printed = None
    sequence = 0
    footnotes: List[ClauseNode] = []
    block_by_page = {}
    for b in blocks:
        if b.pdf_page is not None and b.pdf_page not in block_by_page:
            block_by_page[b.pdf_page] = b

    def _block_id_for(page):
        if page is None:
            return None
        b = block_by_page.get(page)
        return b.block_id if b else None

    def _span(page, text):
        bid = _block_id_for(page)
        if not bid:
            return None
        block = next((b for b in blocks if b.block_id == bid), None)
        if block and text:
            probe = text[:80]
            idx = block.text.find(probe) if probe else -1
            if idx < 0:
                idx = " ".join(block.text.split()).find(" ".join(text.split())[:80])
            if idx >= 0:
                return SourceSpan(block_id=bid, start_char=idx, end_char=idx + len(text))
        return SourceSpan(block_id=bid, start_char=0, end_char=len(text or "")) if bid else None

    def record_artifact(display_id, kind, text, reason, page):
        nonlocal sequence
        sequence += 1
        pages = [page] if isinstance(page, int) else []
        bid = _block_id_for(page)
        inventory.append(
            SourceInventoryRecord(
                node_id=f"artifact:{kind}:{sequence}",
                display_id=display_id,
                node_kind=kind,
                hierarchy=stack.snapshot(),
                sequence_index=sequence,
                start_span=_span(page, text),
                end_span=_span(page, text),
                physical_pdf_pages=pages,
                printed_pages=[current_printed] if current_printed else [],
                source_blocks=[bid] if bid else [],
                disposition="NON_OPERATIVE_ARTIFACT",
                disposition_reason=reason,
                raw_preview=" ".join(text.split())[:180],
            )
        )

    def flush():
        nonlocal current
        if current is None:
            return
        text = current["text"].strip()
        pages = sorted(set(p for p in current["pages"] if isinstance(p, int)))
        flags = list(current["flags"])
        if not pages or any(p is None for p in current["pages"]):
            flags.append("PDF_PAGE_UNRESOLVED")
        if len(pages) > 1:
            flags.append("CROSS_PAGE_CLAUSE")
        flags.extend(ocr_flags(text))
        hier = list(current["hierarchy"])
        cid = current["clause_id"]
        node_id = _scoped_node_id(hier, cid)
        raw_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        spans = current.get("spans") or []
        blocks_ids = list(dict.fromkeys(current.get("block_ids") or []))
        start = spans[0] if spans else _span(pages[0] if pages else None, text)
        display = excerpt(text)
        truncated = len(" ".join(text.split())) > 280
        node = ClauseNode(
            clause_id=cid,
            node_id=node_id,
            display_id=cid,
            parent_clause_id=current.get("parent"),
            parent_node_id=_scoped_node_id(hier, current["parent"]) if current.get("parent") else None,
            node_kind=current.get("kind") or _kind_for(cid),
            hierarchy=hier,
            sequence_index=current["seq"],
            raw_clause_text=text,
            raw_source_text=text,
            applicable_entity=extract_entity(text),
            obligation_type=classify_obligation(text),
            action_required=extract_action(text),
            timeline_sla_penalty=extract_quantitative(text),
            source_pdf_pages=pages,
            physical_pdf_pages=pages,
            printed_page_if_available=printed_for_pages(blocks, pages),
            printed_pages=printed_pages_for(blocks, pages),
            source_blocks=blocks_ids,
            source_spans=spans,
            start_span=start,
            end_span=spans[-1] if spans else start,
            source_excerpt=display,
            display_excerpt=(f"EXCERPT_TRUNCATED {display}" if truncated else display),
            raw_text_sha256=raw_hash,
            raw_source_text_sha256=raw_hash,
            source_pdf_sha256=source_pdf_sha256,
            validation_flags=list(dict.fromkeys(flags)),
            footnote_ids=list(current.get("footnote_ids") or []),
            amendment_effective_date=extract_amendment_date(text),
        )
        nodes.append(node)
        inventory.append(
            SourceInventoryRecord(
                node_id=node_id,
                display_id=cid,
                parent_node_id=node.parent_node_id,
                node_kind=node.node_kind,
                hierarchy=hier,
                sequence_index=current["seq"],
                start_span=start,
                end_span=node.end_span,
                physical_pdf_pages=pages,
                printed_pages=node.printed_pages,
                source_blocks=blocks_ids,
                disposition="EXTRACTED",
                raw_preview=" ".join(text.split())[:180],
            )
        )
        current = None

    def start_node(cid, body_line, parent, kind):
        nonlocal current, sequence
        flush()
        sequence += 1
        bid = _block_id_for(current_pdf_page)
        current = {
            "clause_id": cid,
            "parent": parent,
            "text": body_line,
            "pages": [current_pdf_page],
            "hierarchy": stack.snapshot(),
            "flags": [],
            "kind": kind,
            "seq": sequence,
            "block_ids": [bid] if bid else [],
            "spans": [_span(current_pdf_page, body_line)] if bid else [],
            "footnote_ids": [],
        }

    def append_to_current(line):
        if current is None:
            return
        current["text"] += "\n" + line
        current["pages"].append(current_pdf_page)
        bid = _block_id_for(current_pdf_page)
        if bid and bid not in current["block_ids"]:
            current["block_ids"].append(bid)
        sp = _span(current_pdf_page, line)
        if sp:
            current["spans"].append(sp)

    for raw in markdown.splitlines():
        stripped = raw.strip()
        if ENGINE_MARK.match(stripped):
            continue
        mpage = PAGE_MARK.match(stripped)
        if mpage:
            token = mpage.group(1)
            current_pdf_page = int(token) if token.isdigit() else None
            printed_tok = mpage.group(2)
            current_printed = int(printed_tok) if printed_tok.isdigit() else None
            continue
        if not stripped:
            continue
        if STANDALONE_PAGE.match(stripped) or PRINTED_FOLIO.match(stripped):
            record_artifact(stripped, "printed_page_number", stripped, "printed_folio_or_standalone_page", current_pdf_page)
            continue
        if is_toc_line(stripped):
            record_artifact("TOC", "table_of_contents", stripped, "toc_occurrence_not_operative_clause", current_pdf_page)
            continue
        if stack.update_from_line(stripped) or is_hierarchy_line(stripped):
            kind = "annex_heading" if stripped.lower().startswith("annex") else "heading"
            record_artifact(stripped[:40], kind, stripped, "structural_heading_not_clause_text", current_pdf_page)
            continue
        fn = FOOTNOTE_MARK.match(stripped)
        if fn:
            sequence += 1
            fid = f"footnote:{fn.group('id')}"
            ftext = stripped
            fnode = ClauseNode(
                clause_id=fid,
                node_id=_scoped_node_id(stack.snapshot(), fid),
                display_id=fn.group("id"),
                node_kind="footnote",
                hierarchy=stack.snapshot(),
                sequence_index=sequence,
                raw_clause_text=ftext,
                raw_source_text=ftext,
                source_pdf_pages=[current_pdf_page] if isinstance(current_pdf_page, int) else [],
                physical_pdf_pages=[current_pdf_page] if isinstance(current_pdf_page, int) else [],
                source_excerpt=excerpt(ftext),
                display_excerpt=excerpt(ftext),
                raw_text_sha256=hashlib.sha256(ftext.encode("utf-8")).hexdigest(),
                raw_source_text_sha256=hashlib.sha256(ftext.encode("utf-8")).hexdigest(),
                source_pdf_sha256=source_pdf_sha256,
                amendment_effective_date=extract_amendment_date(ftext),
            )
            footnotes.append(fnode)
            inventory.append(
                SourceInventoryRecord(
                    node_id=fnode.node_id,
                    display_id=fid,
                    node_kind="footnote",
                    hierarchy=stack.snapshot(),
                    sequence_index=sequence,
                    physical_pdf_pages=fnode.physical_pdf_pages,
                    disposition="EXTRACTED",
                    raw_preview=ftext[:180],
                )
            )
            if current is not None:
                current["footnote_ids"].append(fid)
            continue
        mixed = MIXED_NESTED.match(stripped)
        if mixed:
            cid = mixed.group("id")
            body = mixed.group("body") or ""
            start_node(cid, f"{cid} {body}".strip() if body else cid, _parent_of(cid), "mixed_nested_clause")
            continue
        dec = DECIMAL_CLAUSE.match(stripped)
        if dec and not _is_yearish_identifier(dec.group("id").split(".")[0]):
            cid = dec.group("id")
            body = (dec.group("body") or "").strip()
            start_node(cid, f"{cid} {body}".strip(), _parent_of(cid), "decimal_clause")
            continue
        main = MAIN_CLAUSE.match(stripped)
        if main:
            cid = main.group("id")
            if _is_yearish_identifier(cid):
                if current is not None:
                    append_to_current(stripped)
                else:
                    record_artifact(cid, "year_token", stripped, "yearish_identifier_not_clause", current_pdf_page)
                continue
            start_node(cid, _normalize_body(f"{cid}.", main.group("body") or ""), _parent_of(cid), _kind_for(cid))
            continue
        paren = PAREN_CLAUSE.match(stripped)
        if paren and current is not None:
            parent = current["clause_id"]
            cid = f"{parent}{paren.group('id')}"
            body = paren.group("body") or ""
            start_node(cid, f"{cid} {body}".strip(), parent, "parenthetical_clause")
            continue
        if FOOTNOTE_INLINE.match(stripped):
            if current is not None:
                append_to_current(stripped)
            else:
                record_artifact("footnote_inline", "footnote", stripped, "unattached_footnote_marker", current_pdf_page)
            continue
        if current is not None:
            append_to_current(stripped)
        else:
            record_artifact("preamble", "preamble_or_orphan", stripped, "text_outside_numbered_clause", current_pdf_page)

    flush()
    nodes.extend(footnotes)
    _flag_duplicates_and_gaps(nodes)
    _link_footnotes(nodes)
    return ParseResult(nodes, inventory)


def _link_footnotes(nodes: List[ClauseNode]) -> None:
    notes = {n.display_id: n for n in nodes if n.node_kind == "footnote"}
    if not notes:
        return
    for n in nodes:
        if n.node_kind == "footnote":
            continue
        for mid in list(notes.keys()):
            if re.search(rf"(?:\[{re.escape(mid)}\]|{re.escape(mid)}\s*$)", n.raw_source_text):
                if f"footnote:{mid}" not in n.footnote_ids:
                    n.footnote_ids.append(f"footnote:{mid}")


def _flag_duplicates_and_gaps(nodes: List[ClauseNode]) -> List[ClauseNode]:
    seen = {}
    for n in nodes:
        if n.node_kind == "footnote":
            continue
        key = n.node_id or n.clause_id
        seen[key] = seen.get(key, 0) + 1
    dups = {k for k, v in seen.items() if v > 1}
    for n in nodes:
        if (n.node_id or n.clause_id) in dups:
            n.validation_flags.append("DUPLICATE_CLAUSE_ID")
    numeric = []
    for n in nodes:
        if n.node_kind in {"main_clause", "amendment_clause"} and _is_structural_main_id(n.clause_id):
            numeric.append(int("".join(ch for ch in n.clause_id if ch.isdigit())))
    if numeric:
        ordered = sorted(set(numeric))
        gap_starts = {b for a, b in zip(ordered, ordered[1:]) if b - a > 1}
        for n in nodes:
            if n.node_kind in {"main_clause", "amendment_clause"} and _is_structural_main_id(n.clause_id):
                raw = int("".join(ch for ch in n.clause_id if ch.isdigit()))
                if raw in gap_starts:
                    n.validation_flags.append("POTENTIAL_NUMBERING_GAP")
    return nodes


def parse_from_files(markdown_path, page_map_path):
    from pathlib import Path
    from .ingest import load_page_map

    md = Path(markdown_path).read_text(encoding="utf-8")
    blocks = load_page_map(Path(page_map_path))
    return parse_markdown_and_blocks(md, blocks)
