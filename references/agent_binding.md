# Controlled agent binding

Default extraction is standalone. Binding requires `--agent-mode`.

## Contract

`agent_contract.json` plus a read-only adapter

- `get_run_status(run_id)`
- `get_source_manifest(run_id)`
- `list_source_nodes(run_id, filters)`
- `get_source_node(run_id, node_id)`
- `get_evidence(run_id, node_id)`
- `validate_run(run_id)`

Responses are structured data only. They include source hashes, capability mode, validation state, validation flags, and evidence spans. Calls are safe to repeat.

## Preconditions

`agent_bindable: true` only when

- `--agent-mode` was requested, and
- the run is `FULL_VALIDATED`, or an explicitly permitted `COMPATIBILITY_VALIDATED` run with zero material flags.

Otherwise `agent_bindable: false` and a specific block reason.

Run ID is idempotent — hash of source hash + configuration hash + release hash.

## Limits

Permit retrieve-and-cite of source evidence only.

Do not alter source records, update policies, issue compliance conclusions, send communications, or initiate external actions.

Do not transmit PDFs, extracted text, or bank data to external services unless an explicit configuration and authorization permit it.

Log timestamp, request ID, run ID, node IDs accessed, caller-provided purpose, and response status. Do not log source PDFs unnecessarily.

Enforce path allow-lists, output-directory isolation, size limits, input-schema validation, and timeouts.

## Boundary text (verbatim in every adapter response)

RegExtractor provides source evidence only. Regulatory applicability, bank-policy mapping, control design, operating effectiveness, and legal interpretation require separate approved workflows and human review.

## Mapping agent (out of scope)

A separate Compliance Mapping Agent may consume the evidence schema. It must require a bank-policy parser with paragraph/page evidence; applicability, effective dates, product/entity scope, and supersession logic; statuses `COMPLIANT`, `PARTIAL`, `GAP`, `CONTRADICTION`, `NOT_APPLICABLE`, `HUMAN_REVIEW_REQUIRED`; separate policy evidence and RBI evidence for every mapping; Compliance/Legal approval for material determinations; and no autonomous remediation or policy change.
