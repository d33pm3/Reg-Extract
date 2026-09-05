from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import package_root, version

REQUIRED_MODULES = [
    "regextractor.parser",
    "regextractor.ingest",
    "regextractor.validation",
    "regextractor.reconciliation",
    "regextractor.models",
    "regextractor.metadata",
    "regextractor.provenance",
    "regextractor.renderer",
    "regextractor.cli",
]


def _probe(mod: str) -> Dict[str, Any]:
    try:
        importlib.import_module(mod)
        return {"module": mod, "ok": True, "error": None}
    except Exception as exc:
        return {"module": mod, "ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _sha256_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def source_hashes(root: Path) -> Dict[str, str]:
    hashes = {}
    for rel in [
        "VERSION",
        "src/regextractor/parser.py",
        "src/regextractor/ingest.py",
        "src/regextractor/validation.py",
        "src/regextractor/metadata.py",
        "src/regextractor/cli.py",
        "src/regextractor/doctor.py",
    ]:
        digest = _sha256_text(root / rel)
        if digest:
            hashes[rel] = digest
    return hashes


def assess(source_pdf: Optional[Path] = None, out_dir: Optional[Path] = None) -> Dict[str, Any]:
    root = package_root()
    notes: List[str] = []
    checks: Dict[str, Any] = {}
    checks["python"] = {"ok": sys.version_info >= (3, 10), "version": sys.version.split()[0]}
    checks["skill_version"] = version()
    checks["skill_root"] = str(root)
    checks["version_file"] = (root / "VERSION").exists()
    checks["manifest_present"] = (root / "RELEASE_MANIFEST.json").exists()
    checks["lockfile_present"] = (root / "requirements.lock").exists()
    parser_mods = [_probe(m) for m in REQUIRED_MODULES]
    checks["parser_modules"] = parser_mods
    checks["parser_ok"] = all(p["ok"] for p in parser_mods)
    docling = _probe("docling.document_converter")
    pdfplumber = _probe("pdfplumber")
    pydantic = _probe("pydantic")
    checks["docling"] = docling
    checks["mineru"] = {"module": "magic_pdf", "ok": False, "error": "removed_from_fallback_chain_not_installed"}
    checks["pdfplumber"] = pdfplumber
    checks["ocr"] = _probe("pytesseract")
    checks["pydantic"] = pydantic
    page_ok = False
    layout_candidates = []
    if docling["ok"]:
        layout_candidates.append("docling")
    if pdfplumber["ok"]:
        layout_candidates.append("pdfplumber")
        page_ok = True
    ocr = checks.get("ocr") or {}
    if ocr.get("ok"):
        layout_candidates.append("ocr")
    checks["layout_candidates"] = layout_candidates
    checks["physical_page_capability"] = page_ok
    pdf_ok = True
    if source_pdf is not None:
        pdf_ok = source_pdf.exists() and source_pdf.stat().st_size > 0
        checks["source_pdf"] = {"path": str(source_pdf), "ok": pdf_ok}
        if pdf_ok:
            checks["source_sha256"] = hashlib.sha256(source_pdf.read_bytes()).hexdigest()
    else:
        checks["source_pdf"] = {"path": None, "ok": True, "note": "not_supplied"}
    out_ok = True
    if out_dir is not None:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            probe = out_dir / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except Exception as exc:
            out_ok = False
            notes.append(f"output_permission={exc}")
    checks["output_permissions"] = out_ok
    github_imported = any(name.startswith("github") for name in sys.modules)
    checks["source_contamination_github_imported"] = github_imported
    checks["source_hashes"] = source_hashes(root)
    if not checks["parser_ok"] or not checks["pydantic"]["ok"] or not checks["python"]["ok"]:
        capability, reason = "BLOCKED", "mandatory_parser_or_schema_missing"
    elif not page_ok:
        capability, reason = "BLOCKED", "physical_page_provenance_unavailable"
    elif source_pdf is not None and not pdf_ok:
        capability, reason = "BLOCKED", "source_pdf_unreadable"
    elif not out_ok:
        capability, reason = "BLOCKED", "output_not_writable"
    elif docling["ok"] and checks["parser_ok"] and page_ok:
        capability, reason = "FULL_LAYOUT", "docling_and_stage2_operational"
    elif page_ok and checks["parser_ok"]:
        capability, reason = "COMPATIBILITY_LAYOUT", "docling_unavailable_compatibility_parser_present"
        notes.append("layout_engine_will_not_be_labelled_FULL")
    else:
        capability, reason = "BLOCKED", "no_approved_compatibility_path"
    return {"regextractor_version": version(), "capability": capability, "reason": reason, "checks": checks, "notes": notes}


def write_report(report: Dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "runtime_doctor.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "runtime_doctor.md").write_text(
        f"# Runtime Doctor\n\n- Version: {report['regextractor_version']}\n- Capability: {report['capability']}\n- Reason: {report['reason']}\n",
        encoding="utf-8",
    )
    return path


def print_capability(report: Dict[str, Any]) -> None:
    print(report["capability"])
