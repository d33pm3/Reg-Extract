from regextractor.metadata import extract_quantitative


def test_rupee_with_commas_preserved():
    text = "it shall compensate the borrower at the rate of \u20b95,000 for each day of delay."
    q = extract_quantitative(text)
    assert "\u20b95,000" in q
    assert "approximately" not in q
    assert "daily penalty" not in q


def test_inr_and_rs():
    assert "INR 10,000" in extract_quantitative("penalty of INR 10,000 applies")
    assert "Rs. 500" in extract_quantitative("fee of Rs. 500 is levied")


def test_multiple_amounts():
    q = extract_quantitative("up to \u20b95,000 and thereafter \u20b91,00,000")
    assert "\u20b95,000" in q
    assert "\u20b91,00,000" in q


def test_working_vs_calendar_days():
    text = "within 7 working days and not later than 30 calendar days"
    q = extract_quantitative(text)
    assert "working days" in q
    assert "calendar days" in q


def test_no_timeline_is_na():
    assert extract_quantitative("These Directions shall be called the Directions, 2025.") == "N/A"
