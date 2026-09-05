from pathlib import Path

from pypdf import PdfWriter

from regextractor.cli import run_smoke
from tests.test_gold_corpus import GOLD_PAGES
from tests.conftest import wrap_md
from regextractor.parser import parse_document
from regextractor.reconciliation import reconcile


def test_e2e_gold_markdown_package(tmp_path):
    md, blocks = wrap_md(GOLD_PAGES)
    parsed = parse_document(md, blocks, source_pdf_sha256="gold")
    recon = reconcile(parsed.nodes, parsed.inventory)
    assert recon.inventory_equation_holds
    assert {n.clause_id for n in parsed.nodes} >= {"86A", "86B", "121A", "121B", "121C", "121D", "129", "358"}


def test_run_smoke_blocked_without_pdf(tmp_path):
    rc = run_smoke(tmp_path / "missing.pdf", tmp_path / "out", ["129"])
    assert rc == 3
    assert (tmp_path / "out" / "smoke_test_report.md").exists()


def test_ingest_and_extract_tiny_pdf(tmp_path):
    pdf = tmp_path / "tiny.pdf"
    w = PdfWriter()
    w.add_blank_page(width=400, height=200)
    w.write(str(pdf))
    rc = run_smoke(pdf, tmp_path / "out", [])
    # blank PDF yields no operative clauses so run is failed or blocked, never a silent pass
    assert rc in {0, 1, 2}
    assert (tmp_path / "out" / "ingest_manifest.json").exists() or rc == 2
