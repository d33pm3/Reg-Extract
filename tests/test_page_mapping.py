from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_physical_page_from_ingest_marker():
    md, blocks = wrap_md([(47, 47, "129. A bank shall issue duplicate Demand Draft to the customer.")])
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert n.source_pdf_pages == [47]


def test_printed_page_not_equated_when_different():
    md, blocks = wrap_md([(50, 47, "130. The above instructions shall be applicable.")])
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert n.source_pdf_pages == [50]
    assert n.printed_page_if_available == 47


def test_unresolved_page_flagged():
    md = (
        "<!-- SOURCE_ENGINE: fixture -->\n\n"
        "<!-- PDF_PAGE:PDF_PAGE_UNRESOLVED PRINTED_PAGE: -->\n"
        "200. A bank shall maintain records.\n"
    )
    from regextractor.models import PageBlock

    blocks = [
        PageBlock(
            block_id="u1",
            pdf_page=None,
            printed_page=None,
            text="200. A bank shall maintain records.",
            source_engine="fixture",
        )
    ]
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert "PDF_PAGE_UNRESOLVED" in n.validation_flags


def test_ocr_corrupted_token_flagged():
    md, blocks = wrap_md([(1, 1, "12. Compensation of \u20b95\ufffd000 shall be paid.")])
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert "OCR_VALIDATION_REQUIRED" in n.validation_flags
