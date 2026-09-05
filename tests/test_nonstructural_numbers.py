from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_years_and_amounts_are_not_clause_ids():
    md, blocks = wrap_md(
        [
            (
                2,
                2,
                "Reserve Bank of India Directions, 2025\n"
                "Prior circular of 2024 remains withdrawn in 2026.\n"
                "10. A bank shall pay interest within 30 days at 5% or \u20b95,000.",
            )
        ]
    )
    nodes = parse_markdown_and_blocks(md, blocks)
    ids = [n.clause_id for n in nodes]
    assert "2024" not in ids
    assert "2025" not in ids
    assert "2026" not in ids
    assert "30" not in ids
    assert "5" not in ids
    assert "5000" not in ids
    assert "10" in ids
    assert not any(n.clause_id == "2025" for n in nodes)
