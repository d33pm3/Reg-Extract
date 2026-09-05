from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks
from regextractor.reconciliation import reconcile


def test_same_display_id_different_annex_not_duplicate():
    md, blocks = wrap_md(
        [
            (10, 10, "Chapter II – Accounts\n1. A bank shall maintain a register."),
            (80, 80, "Annexure III Forms\n1. Name of the applicant bank."),
        ]
    )
    nodes = parse_markdown_and_blocks(md, blocks)
    ones = [n for n in nodes if n.clause_id == "1"]
    assert len(ones) == 2
    assert ones[0].node_id != ones[1].node_id
    assert "DUPLICATE_CLAUSE_ID" not in ones[0].validation_flags
    assert "DUPLICATE_CLAUSE_ID" not in ones[1].validation_flags
    recon = reconcile(nodes)
    assert "1" not in recon.duplicate_clause_ids
    assert ones[0].clause_id == "1"


def test_true_duplicate_same_scope_still_flagged():
    md, blocks = wrap_md(
        [
            (10, 10, "Chapter II – Accounts\n10. A bank shall do X.\n10. A bank shall do Y."),
        ]
    )
    nodes = parse_markdown_and_blocks(md, blocks)
    tens = [n for n in nodes if n.clause_id == "10"]
    assert len(tens) == 2
    assert tens[0].node_id == tens[1].node_id
    assert "DUPLICATE_CLAUSE_ID" in tens[0].validation_flags
