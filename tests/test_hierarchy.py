from tests.conftest import wrap_md
from regextractor.parser import parse_markdown_and_blocks


def test_chapter_inherited():
    md, blocks = wrap_md(
        [
            (
                47,
                47,
                "Chapter VI – Payment and Remittance Services\nA.3 Issue of Duplicate Demand Draft\n129. A bank shall issue duplicate Demand Draft.",
            )
        ]
    )
    n = parse_markdown_and_blocks(md, blocks)[0]
    joined = " ".join(n.hierarchy)
    assert "Chapter VI" in joined
    assert "Payment" in joined


def test_no_invented_part():
    md, blocks = wrap_md([(1, 1, "Chapter I – Preliminary\n1. These Directions shall apply.")])
    n = parse_markdown_and_blocks(md, blocks)[0]
    assert not any(h.lower().startswith("part ") for h in n.hierarchy)
