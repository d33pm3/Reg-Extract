from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_does_not_merge_numbered_clauses():
    md, blocks = wrap_md([(10, 10, "Chapter II – Test\n1. First clause shall apply.\n2. Second clause shall apply.")])
    nodes = parse_markdown_and_blocks(md, blocks)
    assert [n.clause_id for n in nodes] == ["1", "2"]
    assert "Second clause" not in nodes[0].raw_clause_text


def test_subclauses_are_separate():
    md, blocks = wrap_md([(4, 4, "68. Parent shall apply.\n68(2) A bank shall display the schedule.\n68(2)(a) The display shall include the rate.")])
    ids = [n.clause_id for n in parse_markdown_and_blocks(md, blocks)]
    assert "68" in ids and "68(2)" in ids and "68(2)(a)" in ids


def test_heading_between_clauses_not_merged():
    md, blocks = wrap_md([(5, 5, "5. First shall apply.\nA.2 Encashment of drafts\n6. Next shall apply.")])
    nodes = parse_markdown_and_blocks(md, blocks)
    assert [n.clause_id for n in nodes] == ["5", "6"]
    assert "Encashment" not in nodes[0].raw_clause_text


def test_table_like_lines_stay_in_clause():
    md, blocks = wrap_md([(6, 6, "7. A bank shall publish:\nItem Amount\nFee 10")])
    nodes = parse_markdown_and_blocks(md, blocks)
    assert nodes[0].clause_id == "7"
    assert "Fee 10" in nodes[0].raw_clause_text


def test_duplicate_ids_flagged():
    md, blocks = wrap_md([(8, 8, "Chapter II – X\n10. A bank shall do X.\n10. A bank shall do Y.")])
    nodes = parse_markdown_and_blocks(md, blocks)
    tens = [n for n in nodes if n.clause_id == "10"]
    assert len(tens) == 2
    assert "DUPLICATE_CLAUSE_ID" in tens[0].validation_flags


def test_numbering_gap_flagged_not_fabricated():
    md, blocks = wrap_md([(9, 9, "20. A bank shall A.\n22. A bank shall B.")])
    nodes = parse_markdown_and_blocks(md, blocks)
    assert [n.clause_id for n in nodes] == ["20", "22"]
    assert "POTENTIAL_NUMBERING_GAP" in nodes[1].validation_flags
