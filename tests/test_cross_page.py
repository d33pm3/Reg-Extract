from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_clause_continues_across_pages():
    md, blocks = wrap_md(
        [
            (47, 47, "129. A bank shall issue duplicate Demand Draft to the customer within a fortnight from"),
            (48, 48, "the receipt of such request. Further, for the delay beyond this stipulated period, the bank shall pay interest."),
        ]
    )
    nodes = parse_markdown_and_blocks(md, blocks)
    assert len(nodes) == 1
    n = nodes[0]
    assert n.source_pdf_pages == [47, 48]
    assert "receipt of such request" in n.raw_clause_text
    assert n.page_label() == "47-48"
