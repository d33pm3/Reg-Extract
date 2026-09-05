from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_no_penalty_inferred():
    md, blocks = wrap_md(
        [(3, 3, "Chapter I – Preliminary\n1. These Directions shall be called the Test Directions, 2025.")]
    )
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert n.clause_id == "1"
    assert n.timeline_sla_penalty == "N/A"
    assert "\u20b9" not in n.raw_clause_text


def test_no_entity_is_na():
    md, blocks = wrap_md([(1, 1, "2. Interest means the contractual rate.")])
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert n.applicable_entity == "N/A"


def test_does_not_import_external_context():
    md, blocks = wrap_md([(1, 1, "3. Records shall be retained as specified herein.")])
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert "eight years" not in n.timeline_sla_penalty.lower()
    assert "RBI" not in n.action_required or "shall be retained" in n.action_required
