from regextractor.doctor import assess


def test_doctor_returns_known_capability():
    report = assess(None, None)
    assert report["capability"] in {"FULL_LAYOUT", "COMPATIBILITY_LAYOUT", "BLOCKED"}
    assert report["regextractor_version"]
    assert "parser_ok" in report["checks"]


def test_doctor_does_not_require_github():
    report = assess(None, None)
    assert report["checks"]["source_contamination_github_imported"] is False
