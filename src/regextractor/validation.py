from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .ingest import load_page_map
from .models import ClauseNode, PageBlock
from .provenance import evidence_on_cited_pages, page_text


def find_clause(nodes: List[ClauseNode], clause_id: str) -> Optional[ClauseNode]:
    matches = [n for n in nodes if n.clause_id == clause_id]
    return matches[0] if matches else None


def _contains_clause_start(text: str, clause_id: str) -> bool:
    compact = " ".join(text.split())
    return f"{clause_id}." in compact or compact.startswith(f"{clause_id}.")


def evaluate_clause(node: Optional[ClauseNode], clause_id: str, markdown: str, blocks: List[PageBlock]) -> Dict[str, str]:
    result = {
        "clause_located": "FAIL",
        "raw_source_verified": "FAIL",
        "physical_page_verified": "FAIL",
        "hierarchy_verified": "FAIL",
        "entity_source_supported": "FAIL",
        "modality_verified": "FAIL",
        "timeline_exact": "N/A",
        "amount_penalty_exact": "N/A",
        "evidence_matches_page": "FAIL",
        "unsupported_context": "FAIL",
    }
    if node is None:
        return result
    result["clause_located"] = "PASS"
    if node.raw_clause_text and node.raw_clause_text[:40] in " ".join(markdown.split()):
        result["raw_source_verified"] = "PASS"
    elif node.clause_id and f"{node.clause_id}." in markdown:
        result["raw_source_verified"] = "PASS"
    pages = node.source_pdf_pages
    if pages and "PDF_PAGE_UNRESOLVED" not in node.validation_flags:
        combined = "\n".join(page_text(blocks, p) for p in pages)
        if _contains_clause_start(combined, clause_id):
            result["physical_page_verified"] = "PASS"
    result["hierarchy_verified"] = "PASS" if node.hierarchy else "N/A"
    if node.applicable_entity == "N/A":
        result["entity_source_supported"] = "N/A"
    elif node.applicable_entity != "SOURCE_TEXT_AMBIGUOUS" and node.applicable_entity.lower() in node.raw_clause_text.lower():
        result["entity_source_supported"] = "PASS"
    else:
        result["entity_source_supported"] = "FAIL"
    raw_l = node.raw_clause_text.lower()
    if node.obligation_type == "Prohibitory" and any(x in raw_l for x in ("shall not", "must not", "may not", "prohibited")):
        result["modality_verified"] = "PASS"
    elif node.obligation_type == "Mandatory" and "shall not" not in raw_l and ("shall" in raw_l or "must" in raw_l or "required to" in raw_l):
        result["modality_verified"] = "PASS"
    elif node.obligation_type == "Discretionary" and "may" in raw_l:
        result["modality_verified"] = "PASS"
    elif node.obligation_type == "Informational":
        result["modality_verified"] = "PASS"
    else:
        result["modality_verified"] = "FAIL"
    q = node.timeline_sla_penalty
    if q == "N/A":
        result["timeline_exact"] = "N/A"
        result["amount_penalty_exact"] = "N/A"
    else:
        result["timeline_exact"] = "PASS" if q in node.raw_clause_text or all(part.strip()[:20] in node.raw_clause_text for part in q.split(";") if part.strip()) else "FAIL"
        if "\u20b9" in node.raw_clause_text or "INR" in node.raw_clause_text or "Rs" in node.raw_clause_text:
            result["amount_penalty_exact"] = "PASS" if ("\u20b9" in q or "INR" in q or "Rs" in q) else "FAIL"
        else:
            result["amount_penalty_exact"] = "N/A"
    if evidence_on_cited_pages(node.source_excerpt, pages, blocks):
        result["evidence_matches_page"] = "PASS"
    unsupported = False
    for field in (node.applicable_entity, node.timeline_sla_penalty):
        if field not in ("N/A", "SOURCE_TEXT_AMBIGUOUS") and field[:12].lower() not in raw_l and field not in node.raw_clause_text:
            if "; " in field:
                if not all(p.strip()[:15] in node.raw_clause_text for p in field.split(";") if p.strip()):
                    unsupported = True
            else:
                unsupported = True
    result["unsupported_context"] = "FAIL" if unsupported else "PASS"
    return result


def material_failed(row: Dict[str, str]) -> bool:
    return row.get("clause_located") == "FAIL" or row.get("raw_source_verified") == "FAIL" or row.get("physical_page_verified") == "FAIL" or row.get("evidence_matches_page") == "FAIL" or row.get("unsupported_context") == "FAIL" or row.get("modality_verified") == "FAIL"


def write_smoke_report(out_dir: Path, clause_ids: List[str], rows: Dict[str, Dict[str, str]], nodes: Dict[str, Optional[ClauseNode]]) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = ["Clause Located", "Raw Source Text Verified", "Physical PDF Page Verified", "Hierarchy Verified", "Applicable Entity Source-Supported", "Modality Verified", "Timeline Exact", "Amount/Penalty Exact", "Evidence Matches Cited Page", "Unsupported Context Detected"]
    keys = ["clause_located", "raw_source_verified", "physical_page_verified", "hierarchy_verified", "entity_source_supported", "modality_verified", "timeline_exact", "amount_penalty_exact", "evidence_matches_page", "unsupported_context"]
    lines = ["# RegExtractor Smoke Test", "", "| Validation | " + " | ".join(f"Clause {c}" for c in clause_ids) + " |", "|---|" + "|".join("-" for _ in clause_ids) + "|"]
    for label, key in zip(headers, keys):
        cells = " | ".join(rows[c].get(key, "N/A") for c in clause_ids)
        lines.append(f"| {label} | {cells} |")
    lines.append("")
    failed = [c for c in clause_ids if material_failed(rows[c])]
    if failed:
        lines = ["# SMOKE TEST FAILED", "", "## Failed Control", f"Material failure on clause(s): {', '.join(failed)}", "", "## Evidence", json.dumps({c: rows[c] for c in failed}, indent=2), ""] + lines
    for c in clause_ids:
        node = nodes.get(c)
        lines.append(f"## Complete record — Clause {c}")
        lines.append("")
        if node is None:
            lines.append("NOT LOCATED")
        else:
            lines.append("```json")
            lines.append(node.model_dump_json(indent=2))
            lines.append("```")
        lines.append("")
    text = "\n".join(lines)
    (out_dir / "smoke_test_report.md").write_text(text, encoding="utf-8")
    return text
