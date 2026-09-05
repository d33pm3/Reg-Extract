from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from .models import IngestManifest, PageBlock

logger = logging.getLogger("regextractor.ingest")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _printed_page(text: str) -> Optional[int]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    last = lines[-1]
    if last.isdigit() and 1 <= int(last) <= 9999:
        return int(last)
    return None


def _ingest_pdfplumber(pdf_path: Path) -> Tuple[List[PageBlock], int, str]:
    import pdfplumber

    blocks: List[PageBlock] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            printed = _printed_page(text)
            heading = ""
            for ln in text.splitlines():
                s = ln.strip()
                if s.lower().startswith("chapter ") or s.lower().startswith("annex"):
                    heading = s
                    break
            blocks.append(
                PageBlock(
                    block_id=f"p{i:04d}-b0001",
                    pdf_page=i,
                    printed_page=printed,
                    text=text,
                    heading_context=heading,
                    source_engine="pdfplumber",
                    block_type="page",
                    text_length=len(text),
                    page_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    ocr_status="not_required" if text.strip() else "empty_native_text",
                )
            )
    return blocks, total, "pdfplumber"


def _ingest_docling(pdf_path: Path) -> Tuple[List[PageBlock], int, str]:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document
    blocks: List[PageBlock] = []
    pages_seen = set()
    for idx, item in enumerate(doc.iterate_items()):
        text = getattr(item, "text", None) or str(item)
        prov = getattr(item, "prov", None)
        page = None
        if prov:
            first = prov[0] if isinstance(prov, list) and prov else prov
            page = getattr(first, "page_no", None) or getattr(first, "page", None)
        if page is not None:
            pages_seen.add(int(page))
        blocks.append(
            PageBlock(
                block_id=f"dl-{idx:06d}",
                pdf_page=int(page) if page is not None else None,
                printed_page=None,
                text=text,
                heading_context="",
                source_engine="docling",
                block_type=type(item).__name__,
            )
        )
    total = max(pages_seen) if pages_seen else 0
    if not blocks:
        raise RuntimeError("Docling returned no blocks")
    return blocks, total, "docling"


def ingest_pdf(pdf_path: Path, out_dir: Path) -> IngestManifest:
    out_dir.mkdir(parents=True, exist_ok=True)
    notes: List[str] = []
    engine = "unresolved"
    fallback_used = False
    blocks: List[PageBlock] = []
    total = 0

    try:
        blocks, total, engine = _ingest_docling(pdf_path)
        notes.append("layout_engine=docling")
    except Exception as exc:
        notes.append(f"docling_unavailable={type(exc).__name__}: {exc}")
        notes.append("mineru_not_in_fallback_chain=not_installed")
        logger.warning("Docling unavailable, using pdfplumber: %s", exc)
        fallback_used = True
        blocks, total, engine = _ingest_pdfplumber(pdf_path)
        notes.append("layout_engine=pdfplumber (compatibility, explicit)")

    raw_md_lines = [f"<!-- SOURCE_ENGINE: {engine} -->", ""]
    for b in blocks:
        page = b.pdf_page if b.pdf_page is not None else "PDF_PAGE_UNRESOLVED"
        raw_md_lines.append(f"<!-- PDF_PAGE:{page} PRINTED_PAGE:{b.printed_page or ''} -->")
        raw_md_lines.append(b.text.rstrip())
        raw_md_lines.append("")

    (out_dir / "raw_source.md").write_text("\n".join(raw_md_lines), encoding="utf-8")
    with (out_dir / "page_map.jsonl").open("w", encoding="utf-8") as fh:
        for b in blocks:
            fh.write(b.model_dump_json() + "\n")

    capability = "FULL" if engine == "docling" and not fallback_used else "COMPATIBILITY"
    page_metrics = [
        {
            "pdf_page": b.pdf_page,
            "engine": b.source_engine,
            "text_length": getattr(b, "text_length", len(b.text or "")),
            "ocr_status": getattr(b, "ocr_status", "not_required"),
            "ocr_confidence": getattr(b, "ocr_confidence", None),
            "layout_warnings": getattr(b, "layout_warnings", []),
            "page_sha256": getattr(b, "page_sha256", ""),
        }
        for b in blocks
    ]
    manifest = IngestManifest(
        source_pdf=str(pdf_path),
        source_sha256=sha256_file(pdf_path),
        layout_engine=engine,
        fallback_used=fallback_used,
        total_pdf_pages=total,
        block_count=len(blocks),
        notes=notes,
        page_metrics=page_metrics,
        capability_mode=capability,
    )
    (out_dir / "ingest_manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    return manifest


def load_page_map(path: Path) -> List[PageBlock]:
    blocks = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            blocks.append(PageBlock.model_validate_json(line))
    return blocks
