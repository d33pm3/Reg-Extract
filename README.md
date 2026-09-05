# Reg-Extract

Public source tree for **RegExtractor** — a deterministic, source-only extractor for numbered clauses in regulatory PDFs.

This engine records what the source PDF says. It binds each clause to physical PDF pages, reconciles a Stage-1 source inventory, and flags uncertainty instead of repairing text with model knowledge. It is an extraction engine, not an interpretation engine.

Package name: `regextractor` (v1.3.0)

## What it does

- Ingests a regulatory PDF (native text via pdfplumber; optional Docling layout; optional OCR)
- Parses numbered clauses without merging separately numbered identities
- Maps each node to physical PDF page numbers
- Emits a source inventory plus validation gates
- Optionally exposes a read-only evidence adapter (`--agent-mode`)

## What it does not do

- Legal interpretation, applicability decisions, or policy mapping
- Compliance conclusions, control design, or external actions
- Filling gaps from model memory or the web

## Install

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Optional extras:

```bash
pip install -e ".[ocr]"
pip install -e ".[docling]"
```

## Usage

```bash
regextractor run SOURCE.pdf --out output/
regextractor run SOURCE.pdf --out output/ --agent-mode
regextractor ingest SOURCE.pdf --out work/
regextractor extract --markdown work/raw_source.md --page-map work/page_map.jsonl --out work/result/
regextractor doctor SOURCE.pdf --out work/doctor/
python scripts/smoke_test.py SOURCE.pdf --out work/smoke_test --clauses 129 358
```

See `SKILL.md` for agent-facing operating rules.

## Repository hygiene

This public repository excludes secrets, local environment files, client records, source PDFs, embeddings, and runtime outputs. Do not commit `.env`, keys, tokens, customer artefacts, or private prompts.

## License

See `LICENSE`.
