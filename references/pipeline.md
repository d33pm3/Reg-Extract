# Pipeline fields and tokens

## Stage 1 ingest

`ingest_manifest.json` records the engine actually used (`docling`, `pdfplumber`, or `pdfplumber+ocr`). Compatibility and OCR-risk runs must not be labelled FULL.

Per page — engine, text length, OCR status/confidence, layout warnings, page hash.

Physical PDF page numbers are stored separately from printed folios.

## Stage 1 source inventory

`source_inventory.jsonl` — one record per detected structural token.

Required fields — `node_id`, `display_id`, `parent_node_id`, `node_kind`, `hierarchy`, `sequence_index`, `start_span`, `end_span`, `disposition`.

Disposition is exactly one of

- `EXTRACTED`
- `EXPLICITLY_UNRESOLVED` with a machine-readable reason
- `NON_OPERATIVE_ARTIFACT` with reason and source span

Equation

```
detected_source_nodes = extracted_nodes + explicitly_unresolved_nodes + approved_nonoperative_artifacts
```

Headings, tables-of-contents, footnotes (as artefacts), annex banners, and printed page numbers are structural artefacts, not operative clause text.

A TOC line that merely mentions a clause number is `NON_OPERATIVE_ARTIFACT` and is not evidence for that clause.

## Extracted node evidence

Every extracted node retains

- `source_pdf_sha256`
- `physical_pdf_pages`
- `printed_pages`
- `source_blocks`
- `source_spans` (`block_id`, `start_char`, `end_char`)
- `raw_source_text` (complete, ends before the next source node)
- `raw_source_text_sha256`
- `display_excerpt` (optional; prefix `EXCERPT_TRUNCATED` when shorter than raw)
- `validation_flags`

Validate by source coordinates and full-text reconstruction from cited spans. A 40-character prefix search is not sufficient.

## Parser tokens recognised

- main clauses — `1.`, `129.`, `466.`
- amendment suffixes — `86A.`, `86B.`, `121A.` through `121D.`
- decimal clauses — `1.1`, `1.1.1`
- parenthetical clauses — `(1)`, `(a)`, `(i)`, `(A)`
- mixed nested — `68(2)`, `68(2)(a)`, `68(2)(a)(i)`
- identifiers whose period is not followed by a space — `156.To ...`
- headings, tables, footnotes, annexes, printed page numbers as distinct artefacts

## Failure tokens

`N/A`, `SOURCE_TEXT_AMBIGUOUS`, `OCR_VALIDATION_REQUIRED`, `PDF_PAGE_UNRESOLVED`, `EXPLICITLY_UNRESOLVED`, `DUPLICATE_CLAUSE_ID`, `POTENTIAL_NUMBERING_GAP`, `CROSS_PAGE_CLAUSE`, `CROSS_CLAUSE_LEAKAGE`, `UNLABELLED_QUOTE_CLIPPING`, `STRUCTURAL_AMBIGUITY`.

## Run outcomes

`BLOCKED`, `FAILED`, `COMPATIBILITY_VALIDATED`, `FULL_VALIDATED`.

`agent_bindable` is independent and defaults false.
