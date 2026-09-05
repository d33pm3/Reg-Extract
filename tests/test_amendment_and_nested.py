from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_uppercase_amendment_suffixes():
    md, blocks = wrap_md([(3, 3, "86A. First inserted shall apply.\n86B. Second inserted shall apply.")])
    ids = [n.clause_id for n in parse_markdown_and_blocks(md, blocks)]
    assert ids == ["86A", "86B"]


def test_decimal_and_mixed_nested():
    md, blocks = wrap_md([(4, 4, "1.1 Decimal shall apply.\n68(2)(a)(i) Nested shall apply.")])
    ids = [n.clause_id for n in parse_markdown_and_blocks(md, blocks)]
    assert "1.1" in ids
    assert "68(2)(a)(i)" in ids
