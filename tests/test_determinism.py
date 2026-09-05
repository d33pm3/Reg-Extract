from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def _canon(nodes):
    return [
        (
            n.clause_id,
            tuple(n.hierarchy),
            n.raw_clause_text,
            n.obligation_type,
            n.timeline_sla_penalty,
            tuple(n.source_pdf_pages),
        )
        for n in nodes
    ]


def test_repeated_parse_identical():
    md, blocks = wrap_md(
        [
            (
                104,
                104,
                "Chapter VIII – Responsible Lending Conduct\n"
                "358. A bank shall communicate to the borrower reasons for delay beyond 30 days. "
                "It shall compensate the borrower at the rate of \u20b95,000 for each day of delay.",
            )
        ]
    )
    a = _canon(parse_markdown_and_blocks(md, blocks))
    b = _canon(parse_markdown_and_blocks(md, blocks))
    assert a == b
