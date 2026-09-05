from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .agent import write_agent_contract
from .gates import classify_outcome
from .hashing import config_hash, run_id, write_sha256_manifest
from .models import ClauseNode, IngestManifest, Reconciliation, SourceInventoryRecord
from .paths import version


def _release_hash() -> str:
    from .paths import package_root

    manifest = package_root() / "RELEASE_MANIFEST.json"
    if manifest.exists():
        try:
            return json.loads(manifest.read_text(encoding="utf-8")).get("release_hash", "UNMANIFESTED")
        except Exception:
            return "UNMANIFESTED"
    return "UNMANIFESTED"


def write_run_sidecar(out: Path, nodes, inventory, recon, manifest, smoke_status, doctor) -> None:
    out = Path(out)
    checks = []
    operative = [n for n in nodes if getattr(n, "node_kind", "") != "footnote"]
    def add(gate, target, ok, detail=""):
        checks.append({
            "check_id": f"{gate}:{target}",
            "gate": gate,
            "target": target,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })
    add("zero_detected_operational_clauses", "run", len(operative) > 0, str(len(operative)))
    add("source_inventory_mismatch", "inventory", bool(recon.inventory_equation_holds), recon.inventory_mismatch_detail or "")
    for name in (
        "source_inventory.jsonl", "raw_source.md", "page_map.jsonl", "ingest_manifest.json",
        "clause_ast.jsonl", "output.md", "reconciliation.json", "qa_report.md",
        "smoke_test_report.md", "source_evidence.jsonl",
    ):
        add("required_artifact", name, (out / name).exists())
    failed_checks = []
    # lightweight objects for classify
    class V:
        def __init__(self, d):
            self.gate = d["gate"]
            self.status = d["status"]
    failed_checks = [V(c) for c in checks if c["status"] == "FAIL"]
    outcome = classify_outcome(
        blocked_reason=None,
        failed_checks=failed_checks,
        manifest=manifest,
        nodes=nodes,
        recon=recon,
    )
    if smoke_status.get("overall") == "FAIL":
        outcome["status"] = "FAILED"
        outcome["agent_bindable"] = False
    smoke_status["outcome"] = outcome["status"]
    smoke_status["agent_bindable"] = outcome["agent_bindable"]
    smoke_status["checks_passed"] = sum(1 for c in checks if c["status"] == "PASS")
    smoke_status["checks_total"] = len(checks)
    rid = run_id(manifest.source_sha256, config_hash({"profile": smoke_status.get("profile")}), _release_hash())
    smoke_status["run_id"] = rid
    payload = {
        "outcome": outcome["status"],
        "agent_bindable": outcome["agent_bindable"],
        "block_reason": outcome.get("block_reason"),
        "capability_mode": outcome.get("capability_mode"),
        "command": ["regextractor", "run"],
        "checks_total": len(checks),
        "checks_passed": smoke_status["checks_passed"],
        "checks_failed": sum(1 for c in checks if c["status"] == "FAIL"),
        "checks": checks,
    }
    (out / "validation_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if not (out / "clause_ast.json").exists() and (out / "clause_ast.jsonl").exists():
        rows = []
        for line in (out / "clause_ast.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        (out / "clause_ast.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_agent_contract(out, {
        "run_id": rid,
        "validation_state": outcome["status"],
        "capability_mode": outcome.get("capability_mode"),
        "agent_bindable": False if doctor and doctor.get("capability") == "BLOCKED" else outcome["agent_bindable"],
        "block_reason": outcome.get("block_reason"),
        "source_pdf_sha256": manifest.source_sha256,
        "release_hash": _release_hash(),
        "agent_mode": False,
    })
    write_sha256_manifest(out)
