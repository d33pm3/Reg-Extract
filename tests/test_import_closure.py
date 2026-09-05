def test_import_closure():
    from regextractor.cli import run_smoke, main
    from regextractor import doctor, ingest, parser, validation, renderer, metadata
    from regextractor import bootstrap, paths, profiles, provenance, reconciliation, hierarchy, models
    assert callable(run_smoke)
    assert callable(main)
