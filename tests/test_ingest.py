from pypdf import PdfWriter

from regextractor.ingest import ingest_pdf


def test_ingest_writes_artifacts_and_names_engine(tmp_path):
    pdf = tmp_path / "tiny.pdf"
    w = PdfWriter()
    w.add_blank_page(width=400, height=200)
    w.write(str(pdf))
    out = tmp_path / "out"
    manifest = ingest_pdf(pdf, out)
    assert (out / "raw_source.md").exists()
    assert (out / "page_map.jsonl").exists()
    assert (out / "ingest_manifest.json").exists()
    assert manifest.layout_engine in {"docling", "mineru", "pdfplumber"}
    assert manifest.total_pdf_pages >= 1
    raw = (out / "raw_source.md").read_text(encoding="utf-8")
    assert "SOURCE_ENGINE" in raw
    assert "PDF_PAGE:" in raw
