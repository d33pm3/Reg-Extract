from __future__ import annotations

from typing import List

from .models import ClauseNode, IngestManifest, Reconciliation


def render_output_md(nodes: List[ClauseNode]) -> str:
    parts = [
        "# RegExtractor Clause Register",
        "",
        "Each record packages complete raw source text. Shorter display strings are labelled `EXCERPT_TRUNCATED` and point at `clause_ast.jsonl`.",
        "",
    ]
    for n in nodes:
        pages = n.page_label()
        page_phrase = f"PDF Pages {pages}" if "-" in pages else f"PDF Page {pages}"
        flags = ", ".join(n.validation_flags) if n.validation_flags else "None"
        hier = " > ".join(n.hierarchy) if n.hierarchy else "N/A"
        raw = n.raw_source_text or n.raw_clause_text
        excerpt = n.display_excerpt or n.source_excerpt
        parts.extend(
            [
                f"### Clause {n.clause_id}",
                "",
                f"* **Node ID**: `{n.node_id}`",
                f"* **Kind**: {n.node_kind}",
                f"* **Hierarchy**: {hier}",
                f"* **Applicable Entity**: {n.applicable_entity}",
                f"* **Obligation Type**: {n.obligation_type}",
                f"* **Action Required**: {n.action_required}",
                f"* **Timeline / SLA / Penalty**: {n.timeline_sla_penalty}",
                f"* **Source Reference**: Clause {n.clause_id}, {page_phrase}",
                f"* **Source blocks**: {', '.join(n.source_blocks) or 'N/A'}",
                f"* **Raw text SHA-256**: `{n.raw_source_text_sha256 or n.raw_text_sha256}`",
                f"* **AST record**: `clause_ast.jsonl` node_id=`{n.node_id}`",
                f"* **Display excerpt**: {excerpt}",
                f"* **Validation Flags**: {flags}",
                f"* **Footnotes**: {', '.join(n.footnote_ids) or 'None'}",
                "",
                "```text",
                raw,
                "```",
                "",
            ]
        )
    return "\n".join(parts)


def render_qa_report(manifest: IngestManifest, recon: Reconciliation, smoke_status: dict) -> str:
    overall = smoke_status.get("overall", "NOT_RUN")
    capability = smoke_status.get("capability", "UNKNOWN")
    outcome = smoke_status.get("outcome", "")
    if outcome:
        run_status = outcome
    elif capability in {"FULL", "FULL_LAYOUT"} and overall == "PASS":
        run_status = "FULL_VALIDATED"
    elif overall == "PASS":
        run_status = "COMPATIBILITY_VALIDATED"
    else:
        run_status = overall
    extra_smoke = []
    skip = {
        "overall", "capability", "determinism", "zero_hallucination", "profile",
        "version", "release_hash", "outcome", "agent_bindable", "run_id",
        "checks_passed", "checks_total",
    }
    for key, val in smoke_status.items():
        if key in skip:
            continue
        extra_smoke.append(f"- Clause {key} Smoke Test: {val}")
    return "\n".join(
        [
            "# Extraction QA Summary",
            "",
            f"- RegExtractor version: {smoke_status.get('version', 'UNKNOWN')}",
            f"- Release hash: {smoke_status.get('release_hash', 'UNKNOWN')}",
            f"- Run ID: {smoke_status.get('run_id', 'UNKNOWN')}",
            f"- Source PDF: {manifest.source_pdf}",
            f"- Source SHA-256: {manifest.source_sha256}",
            f"- Layout engine actually used: {manifest.layout_engine}",
            f"- Capability mode: {capability}",
            f"- Validation profile: {smoke_status.get('profile', 'UNKNOWN')}",
            f"- Total PDF Pages: {manifest.total_pdf_pages}",
            f"- Detected source nodes: {recon.detected_source_nodes}",
            f"- Extracted nodes: {recon.extracted_nodes}",
            f"- Explicitly unresolved nodes: {recon.explicitly_unresolved_nodes}",
            f"- Approved non-operative artifacts: {recon.approved_nonoperative_artifacts}",
            f"- Inventory equation holds: {recon.inventory_equation_holds}",
            f"- Total Clauses Identified: {recon.total_clauses_identified}",
            f"- Total Clauses Extracted: {recon.total_clause_nodes_emitted - recon.unresolved_clauses}",
            f"- Explicitly Unresolved Clauses: {recon.unresolved_clauses}",
            f"- Clauses Requiring OCR Validation: {recon.ocr_validation_flags}",
            f"- Clauses With Unresolved PDF Pages: {recon.clauses_without_page_provenance}",
            f"- Cross-Page Clauses: {recon.cross_page_clauses}",
            f"- Duplicate Clause IDs: {', '.join(recon.duplicate_clause_ids) or 'None'}",
            f"- Potential Numbering Gaps: {', '.join(recon.potential_numbering_gaps) or 'None'}",
            *extra_smoke,
            f"- Determinism Tests: {smoke_status.get('determinism', 'NOT_RUN')}",
            f"- Source-only tests: {smoke_status.get('zero_hallucination', 'NOT_RUN')}",
            f"- Checks passed: {smoke_status.get('checks_passed', 'NOT_RUN')} / {smoke_status.get('checks_total', 'NOT_RUN')}",
            f"- Agent bindable: {smoke_status.get('agent_bindable', False)}",
            f"- Source-validation result: {overall}",
            f"- Overall Status: {run_status}",
            "",
            "Observable guarantees: source-only extraction, source hashes, evidence spans, completeness reconciliation, and blocking behaviour for uncertainty. This is not a blanket zero-hallucination claim.",
            "",
        ]
    )
