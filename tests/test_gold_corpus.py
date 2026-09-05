from tests.conftest import wrap_md
from regextractor.parser import parse_document
from regextractor.reconciliation import reconcile


GOLD_PAGES = [
    (
        1,
        1,
        "Reserve Bank of India GOLD FIXTURE Directions, 2025\n"
        "Table of Contents\n"
        "129. Duplicate drafts ................ 47\n"
        "Chapter I – Preliminary\n"
        "1. These GOLD FIXTURE Directions shall apply to test banks.",
    ),
    (
        20,
        20,
        "Chapter IV – Guidance\n"
        "86A. A bank shall publish the GOLD FIXTURE schedule of service charges.\n"
        "86B. A bank shall not levy an unlisted GOLD FIXTURE charge.",
    ),
    (
        40,
        40,
        "Chapter IX – Miscellaneous\n"
        "121. A bank shall maintain GOLD FIXTURE records of customer complaints.\n"
        "B. Inserted obligations\n"
        "121A. A bank shall acknowledge a GOLD FIXTURE complaint within 7 working days.\n"
        "121B. A bank shall resolve a GOLD FIXTURE complaint within 30 calendar days.\n"
        "121C. A bank may escalate a GOLD FIXTURE complaint to the Board.\n"
        "121D. A bank shall not close a GOLD FIXTURE complaint without written reasons.",
    ),
    (
        47,
        47,
        "Chapter VI – Payment\n"
        "A.3 Issue of Duplicate Demand Draft\n"
        "129. A bank shall issue duplicate Demand Draft to the customer within a fortnight.",
    ),
    (
        55,
        55,
        "156.To display the GOLD FIXTURE rates a bank shall use the notice board.",
    ),
    (
        70,
        70,
        "281. [Deleted]4\n"
        "4 Deleted with effect from April 1, 2026",
    ),
    (
        80,
        80,
        "321. A bank shall pay GOLD FIXTURE compensation of \u20b95,000 within 15 days.\n"
        "322. Interest at the rate of 8% shall apply after 30 calendar days.",
    ),
    (
        90,
        90,
        "Chapter VIII – Responsible Lending Conduct\n"
        "358. A bank shall communicate to the borrower reasons for delay beyond 30 days. "
        "It shall compensate the borrower at the rate of \u20b95,000 for each day of delay.",
    ),
    (
        100,
        100,
        "466. For the purpose of giving effect to these GOLD FIXTURE Directions the interpretation of the test authority shall be final.\n"
        "68. Parent GOLD FIXTURE duty shall apply.\n"
        "68(2) A bank shall display the GOLD FIXTURE schedule.\n"
        "68(2)(a) The display shall include the GOLD FIXTURE rate.",
    ),
    (
        110,
        110,
        "A long GOLD FIXTURE clause starts here and continues",
    ),
    (
        111,
        111,
        "across the following physical page without starting a new number.",
    ),
    (
        120,
        120,
        "Annexure III Forms\n"
        "1. Name of the applicant GOLD FIXTURE bank.",
    ),
]


def _parse():
    md, blocks = wrap_md(GOLD_PAGES)
    parsed = parse_document(md, blocks, source_pdf_sha256="gold-fixture")
    return parsed


def test_gold_ids_are_separate():
    nodes = _parse().nodes
    ids = [n.clause_id for n in nodes]
    for required in ("86A", "86B", "121", "121A", "121B", "121C", "121D", "129", "156", "281", "321", "322", "358", "466"):
        assert required in ids, required


def test_121_does_not_include_heading_or_121A():
    n = next(n for n in _parse().nodes if n.clause_id == "121")
    assert "121A" not in n.raw_source_text
    assert "Inserted obligations" not in n.raw_source_text


def test_156_no_space_after_period():
    n = next(n for n in _parse().nodes if n.clause_id == "156")
    assert n.raw_source_text.startswith("156.To")


def test_281_links_footnote_4():
    parsed = _parse()
    n = next(n for n in parsed.nodes if n.clause_id == "281")
    assert "[Deleted]4" in n.raw_source_text or n.raw_source_text.endswith("4")
    assert any(fid.endswith("4") or fid == "footnote:4" for fid in n.footnote_ids) or any(
        x.clause_id == "footnote:4" for x in parsed.nodes
    )


def test_monetary_and_timing_preserved():
    parsed = _parse()
    n321 = next(n for n in parsed.nodes if n.clause_id == "321")
    n358 = next(n for n in parsed.nodes if n.clause_id == "358")
    assert "\u20b95,000" in n321.raw_source_text
    assert "15 days" in n321.timeline_sla_penalty or "15 days" in n321.raw_source_text
    assert "\u20b95,000" in n358.raw_source_text
    assert "30 days" in n358.raw_source_text


def test_inventory_equation_and_toc_not_operative():
    parsed = _parse()
    recon = reconcile(parsed.nodes, parsed.inventory)
    assert recon.inventory_equation_holds
    toc = [r for r in parsed.inventory if r.node_kind == "table_of_contents"]
    assert toc
    n129 = [n for n in parsed.nodes if n.clause_id == "129"]
    assert len(n129) == 1
    assert n129[0].source_pdf_pages == [47]


def test_annex_repeat_not_duplicate_of_chapter_one():
    nodes = [n for n in _parse().nodes if n.clause_id == "1"]
    assert len(nodes) == 2
    assert nodes[0].node_id != nodes[1].node_id
    assert "DUPLICATE_CLAUSE_ID" not in nodes[0].validation_flags
