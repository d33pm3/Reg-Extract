---
name: regextractor
description: Deterministic source-only extractor for numbered clauses in regulatory PDFs (RBI Master Directions, circulars, gazette instruments). Use when asked to extract obligations, build a clause register, map physical PDF pages, run RegExtractor, smoke-test clauses such as 129 and 358, emit a source inventory, or bind a read-only evidence adapter. Never answer those questions from model memory.
author: DK Mendiratta
metadata:
  version: "1.3.0"
  type: workflow
  author: DK Mendiratta
---

# RegExtractor

Run the bundled Python pipeline. Do not answer regulatory content from memory. The system's role is source extraction and evidence validation, not legal interpretation, legal advice, policy-compliance determination, control-effectiveness testing, or autonomous regulatory action.

## When to activate

Activate when the user supplies or points to a regulatory PDF and asks for clause extraction, a source register, obligation listing, page provenance, a smoke test of named clauses, a source inventory, or optional read-only agent binding.

Do not activate for bank-policy-to-RBI mapping, control design, or legal opinions. Publish evidence only. Mapping belongs to a separate agent.

## Supported and unsupported PDF types

Supported

- Native-text regulatory PDFs with numbered clauses (pdfplumber compatibility path).
- Layout-aware native PDFs when the optional Docling extra is installed and its tested API succeeds.
- Low-text or scanned pages when the OCR extra (pytesseract) is installed. Those runs are never labelled FULL.

Unsupported / blocked

- Empty or blank PDFs.
- Scanned PDFs with no usable OCR engine or empty OCR output on pages expected to contain operative text.
- Password-protected or unreadable files.
- Invented corpora used to fill gaps in a supplied PDF.

MinerU is not in the fallback chain (not installed, not advertised).

## Hard rules

- Extract only what the source PDF says. Never use model memory, web content, or inferred wording to fill a gap.
- Never merge separately numbered clauses, including `86A`, `121A` through `121D`, `1.1`, `(a)`, `(i)`, or `68(2)(a)(i)`.
- Never silently truncate a source quote. Complete raw text stays in the package. A shorter display string must be labelled `EXCERPT_TRUNCATED` and linked to the AST record.
- Never emit `PASS`, `FULL_PASS`, `AGENT_BINDABLE`, or `READY_FOR_MAPPING` for an empty clause inventory, incomplete source inventory, unresolved page, OCR-risk node, duplicate identity, structural ambiguity, or failed evidence check.
- Preserve physical PDF page numbers separately from printed folios.
- A table-of-contents occurrence of a clause number is not evidence for the operative clause.
- Do not create compliance conclusions, policy mappings, controls, legal opinions, or external actions from this skill alone.

Preferred failure tokens — `N/A`, `SOURCE_TEXT_AMBIGUOUS`, `OCR_VALIDATION_REQUIRED`, `PDF_PAGE_UNRESOLVED`, `EXPLICITLY_UNRESOLVED`.

Forbidden failure — plausible text that is not in the source clause.

## Workflow

1. Confirm a source PDF path exists. If absent, stop with `SMOKE_TEST_STATUS = BLOCKED_SOURCE_PDF_REQUIRED` and still ship the code/tests.
2. Stage 1 — `regextractor ingest SOURCE.pdf --out work/`
   - Attempt Docling only when the installed API is present.
   - Compatibility path is pdfplumber for native-text pages.
   - Controlled OCR path fills empty/low-text pages when pytesseract is present.
   - Record the engine actually used in `ingest_manifest.json`. Do not silently relabel it. Do not label compatibility or OCR-risk runs FULL.
3. Stage 2 — `regextractor extract --markdown work/raw_source.md --page-map work/page_map.jsonl --out work/result/`
4. Runtime doctor — `regextractor doctor SOURCE.pdf --out work/doctor/` prints `FULL_LAYOUT`, `COMPATIBILITY_LAYOUT`, or `BLOCKED`. FULL_LAYOUT requires Docling.
5. End-to-end — `regextractor run SOURCE.pdf --out output/`
   Optional agent binding — `regextractor run SOURCE.pdf --out output/ --agent-mode`
6. Validation clauses come from `config/profiles`. The RBI RBC 2025 profile lists 129 and 358 as IDs only. A generic profile with no configured IDs must still be tested against discovered source nodes. An empty test set is not a pass.
7. After install, extraction must not contact GitHub.

Parser completeness is the Stage-1 source inventory, not a numeric range such as `1..466`.

## Commands

Package root is this skill directory when running inside Grok.

```bash
pip install -e ".[dev]"
PYTHONPATH=src python -m regextractor.cli ingest SOURCE.pdf --out work/
PYTHONPATH=src python -m regextractor.cli run SOURCE.pdf --out output/
PYTHONPATH=src python -m regextractor.cli run SOURCE.pdf --out output/ --agent-mode
PYTHONPATH=src python -m regextractor.cli doctor SOURCE.pdf --out work/doctor/
pytest -q
python scripts/smoke_test.py SOURCE.pdf --out work/smoke_test --clauses 129 358
python scripts/make_release.py
bash scripts/install_grok.sh ./dist/RegExtractor-Grok-1.3.0.zip /tmp/regextractor-install
bash scripts/uninstall_grok.sh /tmp/regextractor-install
```

Console entry point after install — `regextractor = "regextractor.cli:main"`.

## Evidence package

A successful run writes a self-contained package under `--out`

```text
output/
├── source_inventory.jsonl
├── raw_source.md
├── page_map.jsonl
├── ingest_manifest.json
├── clause_ast.jsonl
├── clause_ast.json
├── output.md
├── reconciliation.json
├── qa_report.md
├── validation_results.json
├── smoke_test_report.md
├── source_evidence.jsonl
├── agent_contract.json
└── MANIFEST.sha256
```

`output.md` includes the complete raw text for every source node, or an `EXCERPT_TRUNCATED` excerpt plus a local AST pointer. Do not refer to undeployed paths.

If an output says `N checks passed`, `validation_results.json` lists those N results and the command used.

## Failure statuses

Run outcomes are only

- `BLOCKED`
- `FAILED`
- `COMPATIBILITY_VALIDATED`
- `FULL_VALIDATED`

`AGENT_BINDABLE` is a separate flag. It may be set only after agent-binding gates pass.

Material failure conditions (non-zero exit)

- zero detected operational clauses
- zero extracted clauses where operational clauses were detected
- source-inventory mismatch
- omitted or duplicate source node identity
- unrecognised amendment suffix or structural token
- page provenance missing, ambiguous, or inconsistent
- raw text not equal to the cited source spans
- cross-clause leakage
- unlabelled quote clipping
- OCR validation required on an operative node
- failed required smoke fixture
- absent required output artifact
- release manifest / file-hash mismatch

Inventory equation (independently computed)

```text
detected_source_nodes = extracted_nodes + explicitly_unresolved_nodes + approved_nonoperative_artifacts
```

Do not calculate `identified = emitted` by definition.

## Controlled agent binding

Default extraction is standalone and non-agentic. Binding requires explicit `--agent-mode`.

Read-only adapter methods — `get_run_status`, `get_source_manifest`, `list_source_nodes`, `get_source_node`, `get_evidence`, `validate_run`.

Set `agent_bindable: true` only for a `FULL_VALIDATED` run, or an explicitly permitted `COMPATIBILITY_VALIDATED` run with zero material flags. Otherwise return `agent_bindable: false` and a block reason.

Agents may retrieve and cite source evidence. They may not alter source records, update policies, issue compliance conclusions, send communications, or initiate external actions.

Every adapter response includes this boundary

> RegExtractor provides source evidence only. Regulatory applicability, bank-policy mapping, control design, operating effectiveness, and legal interpretation require separate approved workflows and human review.

See `references/agent_binding.md`.

## Mapping boundary

Do not implement bank-policy-to-RBI compliance mapping inside RegExtractor. Publish the evidence schema in `source_evidence.jsonl` and `agent_contract.json` for a separate Compliance Mapping Agent. That agent needs its own policy parser, applicability rules, dual evidence, human approval, and no autonomous remediation.

## Observable guarantees

Do not claim blanket "zero hallucination". State the guarantees that can be observed

- source-only extraction
- source hashes
- evidence spans
- completeness reconciliation
- blocking behaviour for uncertainty

Field definitions and tokens — `references/pipeline.md`. Validation gates — `references/validation_gates.md`.

## Implementation map

- Stage 1 ingest — `src/regextractor/ingest.py`
- Grammar parser and inventory — `src/regextractor/parser.py`
- Provenance — `src/regextractor/provenance.py`
- Gates — `src/regextractor/gates.py` and `src/regextractor/validation.py`
- Agent adapter — `src/regextractor/agent.py`
- CLI — `src/regextractor/cli.py`
