from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks
from regextractor.validation import evaluate_clause, find_clause, material_failed


def test_smoke_harness_passes_on_fixture_source():
    md, blocks = wrap_md(
        [
            (
                47,
                47,
                "Chapter VI – Payment\n129. A bank shall issue duplicate Demand Draft to the customer within a fortnight.",
            ),
            (
                104,
                104,
                "F.2 Compensation\n358. A bank shall communicate to the borrower reasons for delay beyond 30 days. "
                "It shall compensate the borrower at the rate of \u20b95,000 for each day of delay.",
            ),
        ]
    )
    nodes = parse_markdown_and_blocks(md, blocks)
    for cid in ("129", "358"):
        node = find_clause(nodes, cid)
        row = evaluate_clause(node, cid, md, blocks)
        assert row["clause_located"] == "PASS"
        assert not material_failed(row), row
