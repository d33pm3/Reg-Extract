import io
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfWriter

from regextractor.archive_safety import UnsafeArchiveError, validate_zip_members
from regextractor.agent import AgentAdapter, write_agent_contract
from regextractor.ingest import ingest_pdf
from regextractor.parser import parse_document
from tests.conftest import wrap_md


def test_empty_pdf_still_writes_artifacts(tmp_path):
    pdf = tmp_path / "blank.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(str(pdf))
    out = tmp_path / "out"
    manifest = ingest_pdf(pdf, out)
    assert (out / "raw_source.md").exists()
    assert manifest.layout_engine in {"pdfplumber", "docling"}


def test_toc_false_match_not_operative():
    md, blocks = wrap_md([(1, 1, "129. Duplicate drafts ................ 47\nChapter I – X\n2. Operative GOLD FIXTURE clause shall apply.")])
    parsed = parse_document(md, blocks)
    ids = [n.clause_id for n in parsed.nodes]
    assert "2" in ids
    assert "129" not in ids or any(r.node_kind == "table_of_contents" for r in parsed.inventory)


def test_zip_path_traversal_rejected(tmp_path):
    zpath = tmp_path / "evil.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../escape.txt", "nope")
    with zipfile.ZipFile(zpath) as zf:
        with pytest.raises(UnsafeArchiveError):
            validate_zip_members(zf)


def test_agent_not_bindable_when_disabled(tmp_path):
    write_agent_contract(tmp_path, {"run_id": "abc", "validation_state": "FAILED", "agent_bindable": False, "block_reason": "failed"})
    adapter = AgentAdapter(tmp_path, agent_mode=False)
    status = adapter.get_run_status("abc")
    assert status["agent_bindable"] is False
    adapter2 = AgentAdapter(tmp_path, agent_mode=True)
    status2 = adapter2.get_run_status("abc")
    assert status2["agent_bindable"] is False
    assert "RegExtractor provides source evidence only" in status2["boundary"]


def test_generic_profile_empty_ids_uses_discovered():
    from regextractor.profiles import clause_ids_for
    ids = clause_ids_for({"profile_id": "generic", "validation_clauses": []}, ["10", "20", "30"])
    assert ids
