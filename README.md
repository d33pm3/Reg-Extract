# Reg-Extract

**Author:** DK Mendiratta

Public source tree for **RegExtractor** — a deterministic, source-only extractor for numbered clauses in regulatory PDFs.

This engine records what the source PDF says. It binds each clause to physical PDF pages, reconciles a Stage-1 source inventory, and flags uncertainty instead of repairing text with model knowledge. It is an extraction engine, not an interpretation engine.

Package name: `regextractor` (v1.3.0)

## This is / this is not

**This is** a local deterministic extractor for numbered clauses in regulatory PDFs (`regextractor` v1.3.0).
**This is** a source-only engine that binds each clause to physical PDF pages and flags uncertainty.
**This is** a CLI plus an optional read-only evidence adapter (`--agent-mode`).
**This is not** Policy-Extract, a RACM builder, or a bank-policy-to-regulation mapper.
**This is not** a live-web researcher.
**This is not** a legal opinion or an applicability decision.
**This is not** a hosted API or web app.
**This is not** a shipped corpus — bring your own PDF; none is in this repo.

## Why it exists

Numbered regulatory PDFs fail two ways in model-led extraction: separately numbered identities such as `86A` and `121A` get merged into a neighbour, and missing text is invented from model memory. This engine keeps each numbered identity distinct, binds it to physical PDF pages, and blocks when the source is uncertain instead of repairing the gap.

## Who it is for

- Company secretaries and compliance heads who need a clause register with page provenance
- GRC advisors who must separate source text from later mapping work
- RegTech implementors wiring an evidence package into a downstream workflow
- Clause-register builders
- AI agent builders who need a read-only evidence adapter (`--agent-mode`)

Publish evidence; mapping is another workflow.

## What it does

- Ingests a regulatory PDF (native text via pdfplumber; optional Docling layout; optional OCR)
- Parses numbered clauses without merging separately numbered identities
- Maps each node to physical PDF page numbers
- Emits a source inventory plus validation gates
- Optionally exposes a read-only evidence adapter (`--agent-mode`)

## What it does not do

- Control design or external actions

Legal interpretation, applicability, policy mapping, compliance conclusions, and filling gaps from model memory or the web are covered in **This is / this is not** above.

## Use the CLI

Local package only. After install it does not contact GitHub. Bring your own PDF; none is shipped.

Requires Python 3.10+.

```bash
git clone https://github.com/d33pm3/Reg-Extract.git
cd Reg-Extract
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest -q
regextractor run /path/to/SOURCE.pdf --out output/
regextractor doctor /path/to/SOURCE.pdf --out work/doctor/
```

Stage commands if you need them separately:

```bash
regextractor ingest /path/to/SOURCE.pdf --out work/
regextractor extract --markdown work/raw_source.md --page-map work/page_map.jsonl --out work/result/
python scripts/smoke_test.py /path/to/SOURCE.pdf --out work/smoke_test --clauses 129 358
```

Optional extras:

```bash
pip install -e ".[ocr]"
pip install -e ".[docling]"
```

## Bind an agent

Default extraction is standalone and non-agentic.

1. Install as above.
2. Drop `SKILL.md` into the skill host (Claude Skills, Cursor, Grok custom skills, or equivalent).
3. Run `regextractor run /path/to/SOURCE.pdf --out output/ --agent-mode`.
4. Agents may read evidence (`get_run_status`, `get_source_manifest`, `list_source_nodes`, `get_source_node`, `get_evidence`, `validate_run`). They may not alter source records or issue compliance conclusions.

See `SKILL.md` for operating rules.

## Optional Grok zip install

```bash
python scripts/make_release.py
bash scripts/install_grok.sh ./dist/RegExtractor-Grok-1.3.0.zip /tmp/regextractor-install
bash scripts/uninstall_grok.sh /tmp/regextractor-install
```

That drops a local skill tree. It is not a hosted API.

## Output package

A successful `regextractor run SOURCE.pdf --out output/` writes:

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

## Repository hygiene

This public repository excludes secrets, local environment files, client records, source PDFs, embeddings, and runtime outputs. Do not commit `.env`, keys, tokens, customer artefacts, or private prompts.

## License

MIT. See `LICENSE`.

You may use this code; the extract is not a legal opinion or a compliance conclusion.
