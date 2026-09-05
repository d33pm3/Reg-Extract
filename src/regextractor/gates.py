from __future__ import annotations

from typing import List, Optional

from .models import ClauseNode, IngestManifest, Reconciliation, ValidationCheck


def classify_outcome(
    *,
    blocked_reason: Optional[str],
    failed_checks: List[ValidationCheck],
    manifest: Optional[IngestManifest],
    nodes: List[ClauseNode],
    recon: Optional[Reconciliation],
    permit_compat_bind: bool = True,
) -> dict:
    if blocked_reason:
        return {
            "status": "BLOCKED",
            "agent_bindable": False,
            "block_reason": blocked_reason,
            "capability_mode": (manifest.capability_mode if manifest else "UNKNOWN"),
        }
    if failed_checks:
        return {
            "status": "FAILED",
            "agent_bindable": False,
            "block_reason": ",".join(sorted({c.gate for c in failed_checks})),
            "capability_mode": (manifest.capability_mode if manifest else "UNKNOWN"),
        }
    ocr_risk = any("OCR_VALIDATION_REQUIRED" in n.validation_flags for n in nodes)
    dups = any("DUPLICATE_CLAUSE_ID" in n.validation_flags for n in nodes)
    unresolved_page = any(
        "PDF_PAGE_UNRESOLVED" in n.validation_flags for n in nodes if not n.unresolved and n.node_kind != "footnote"
    )
    if recon and not recon.inventory_equation_holds:
        return {
            "status": "FAILED",
            "agent_bindable": False,
            "block_reason": "source_inventory_mismatch",
            "capability_mode": manifest.capability_mode if manifest else "UNKNOWN",
        }
    capability = manifest.capability_mode if manifest else "COMPATIBILITY"
    status = "FULL_VALIDATED" if capability == "FULL" and not ocr_risk else "COMPATIBILITY_VALIDATED"
    material = ocr_risk or dups or unresolved_page
    bindable = (status == "FULL_VALIDATED") or (status == "COMPATIBILITY_VALIDATED" and permit_compat_bind and not material)
    return {
        "status": status,
        "agent_bindable": bindable,
        "block_reason": None if bindable else ("material_flags" if material else None),
        "capability_mode": capability,
    }
