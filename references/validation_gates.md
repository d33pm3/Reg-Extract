# Validation gates

A run returns non-zero when any material gate fails.

Gates

1. zero detected operational clauses
2. zero extracted clauses where operational clauses were detected
3. source-inventory mismatch
4. omitted or duplicate source node identity
5. unrecognised amendment suffix or structural token
6. page provenance missing, ambiguous, or inconsistent
7. raw text not equal to the cited source spans
8. cross-clause leakage
9. unlabelled quote clipping
10. OCR validation requirement on an operative node
11. failed required smoke fixture
12. absent required output artifact
13. release manifest / file-hash mismatch

Generic profile with no configured smoke IDs — test discovered source nodes. An empty test set is not a pass.

Never emit PASS / FULL_PASS / AGENT_BINDABLE / READY_FOR_MAPPING when any gate above is open.

`validation_results.json` lists every check. If a report says N checks passed, those N rows exist in that file together with the command used.
