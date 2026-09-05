from __future__ import annotations

from collections import Counter
from typing import List, Optional

from .models import ClauseNode, Reconciliation, SourceInventoryRecord


def reconcile(
    nodes: List[ClauseNode], inventory: Optional[List[SourceInventoryRecord]] = None
) -> Reconciliation:
    ids = [n.node_id or n.clause_id for n in nodes if n.node_kind != "footnote"]
    counts = Counter(ids)
    dups = sorted([cid for cid, c in counts.items() if c > 1])
    unresolved_nodes = [n for n in nodes if n.unresolved]
    no_page = [
        n
        for n in nodes
        if n.node_kind != "footnote"
        and (not n.source_pdf_pages or "PDF_PAGE_UNRESOLVED" in n.validation_flags)
    ]
    cross = [n for n in nodes if len(set(n.source_pdf_pages)) > 1]
    ocr = [n for n in nodes if "OCR_VALIDATION_REQUIRED" in n.validation_flags]
    hier = [n for n in nodes if "HIERARCHY_ANOMALY" in n.validation_flags]
    gaps = [n.clause_id for n in nodes if "POTENTIAL_NUMBERING_GAP" in n.validation_flags]
    emitted = len([n for n in nodes if n.node_kind != "footnote"])
    extracted = len([n for n in nodes if not n.unresolved and n.node_kind != "footnote"])

    if inventory is not None:
        detected = len(inventory)
        inv_extracted = len([r for r in inventory if r.disposition == "EXTRACTED"])
        inv_unresolved = len([r for r in inventory if r.disposition == "EXPLICITLY_UNRESOLVED"])
        inv_artifacts = len([r for r in inventory if r.disposition == "NON_OPERATIVE_ARTIFACT"])
        equation = detected == inv_extracted + inv_unresolved + inv_artifacts
        detail = None if equation else (
            f"detected={detected} extracted={inv_extracted} unresolved={inv_unresolved} artifacts={inv_artifacts}"
        )
        return Reconciliation(
            detected_source_nodes=detected,
            extracted_nodes=inv_extracted,
            explicitly_unresolved_nodes=inv_unresolved,
            approved_nonoperative_artifacts=inv_artifacts,
            total_clauses_identified=detected,
            total_clause_nodes_emitted=emitted,
            unique_clause_ids=len(counts),
            duplicate_clause_ids=dups,
            potential_numbering_gaps=sorted(set(gaps)),
            unresolved_clauses=inv_unresolved,
            clauses_without_page_provenance=len(no_page),
            cross_page_clauses=len(cross),
            ocr_validation_flags=len(ocr),
            hierarchy_anomalies=len(hier),
            inventory_equation_holds=equation,
            inventory_mismatch_detail=detail,
        )

    identified = extracted + len(unresolved_nodes)
    return Reconciliation(
        detected_source_nodes=identified,
        extracted_nodes=extracted,
        explicitly_unresolved_nodes=len(unresolved_nodes),
        approved_nonoperative_artifacts=0,
        total_clauses_identified=identified,
        total_clause_nodes_emitted=emitted,
        unique_clause_ids=len(counts),
        duplicate_clause_ids=dups,
        potential_numbering_gaps=sorted(set(gaps)),
        unresolved_clauses=len(unresolved_nodes),
        clauses_without_page_provenance=len(no_page),
        cross_page_clauses=len(cross),
        ocr_validation_flags=len(ocr),
        hierarchy_anomalies=len(hier),
        inventory_equation_holds=identified == extracted + len(unresolved_nodes),
        inventory_mismatch_detail="inventory_absent_legacy_equation",
    )
