from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

BOUNDARY = (
    "RegExtractor provides source evidence only. Regulatory applicability, "
    "bank-policy mapping, control design, operating effectiveness, and legal "
    "interpretation require separate approved workflows and human review."
)


class AgentAdapter:
    def __init__(self, output_dir: Path, agent_mode: bool = False):
        self.output_dir = Path(output_dir)
        self.agent_mode = agent_mode
        self.log_path = self.output_dir / "agent_access.log"

    def _contract(self) -> Dict[str, Any]:
        path = self.output_dir / "agent_contract.json"
        if not path.exists():
            return {
                "agent_bindable": False,
                "block_reason": "agent_contract_missing",
                "validation_state": "BLOCKED",
                "boundary": BOUNDARY,
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def _log(self, method: str, run_id: str, node_ids: List[str], purpose: str, status: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rec = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": str(uuid.uuid4()),
            "method": method,
            "run_id": run_id,
            "node_ids": node_ids,
            "purpose": purpose,
            "status": status,
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")

    def _guard(self, run_id: str) -> Dict[str, Any]:
        if not self.agent_mode:
            return {"ok": False, "error": "agent_mode_disabled", "agent_bindable": False, "boundary": BOUNDARY}
        contract = self._contract()
        if contract.get("run_id") and contract["run_id"] != run_id:
            return {"ok": False, "error": "run_id_mismatch", "agent_bindable": False, "boundary": BOUNDARY}
        return {"ok": True, "contract": contract}

    def get_run_status(self, run_id: str, purpose: str = "") -> Dict[str, Any]:
        g = self._guard(run_id)
        self._log("get_run_status", run_id, [], purpose, "ok" if g.get("ok") else "blocked")
        if not g.get("ok"):
            return {**g, "boundary": BOUNDARY}
        c = g["contract"]
        return {
            "run_id": run_id,
            "validation_state": c.get("validation_state"),
            "capability_mode": c.get("capability_mode"),
            "agent_bindable": c.get("agent_bindable", False),
            "block_reason": c.get("block_reason"),
            "source_pdf_sha256": c.get("source_pdf_sha256"),
            "release_hash": c.get("release_hash"),
            "boundary": BOUNDARY,
        }

    def get_source_manifest(self, run_id: str, purpose: str = "") -> Dict[str, Any]:
        g = self._guard(run_id)
        self._log("get_source_manifest", run_id, [], purpose, "ok" if g.get("ok") else "blocked")
        if not g.get("ok"):
            return g
        if not g["contract"].get("agent_bindable"):
            return {"agent_bindable": False, "block_reason": g["contract"].get("block_reason") or "not_agent_bindable", "boundary": BOUNDARY}
        manifest = json.loads((self.output_dir / "ingest_manifest.json").read_text(encoding="utf-8"))
        return {"run_id": run_id, "manifest": manifest, "boundary": BOUNDARY, "agent_bindable": True}

    def list_source_nodes(self, run_id: str, filters: Optional[Dict[str, Any]] = None, purpose: str = "") -> Dict[str, Any]:
        g = self._guard(run_id)
        self._log("list_source_nodes", run_id, [], purpose, "ok" if g.get("ok") else "blocked")
        if not g.get("ok") or not g["contract"].get("agent_bindable"):
            return {"agent_bindable": False, "block_reason": (g.get("error") or (g.get("contract") or {}).get("block_reason")), "boundary": BOUNDARY}
        nodes = json.loads((self.output_dir / "clause_ast.json").read_text(encoding="utf-8"))
        filters = filters or {}
        out = []
        for n in nodes:
            if filters.get("clause_id") and n.get("clause_id") != filters["clause_id"]:
                continue
            if filters.get("node_kind") and n.get("node_kind") != filters["node_kind"]:
                continue
            out.append({
                "node_id": n.get("node_id"),
                "display_id": n.get("display_id") or n.get("clause_id"),
                "node_kind": n.get("node_kind"),
                "physical_pdf_pages": n.get("physical_pdf_pages") or n.get("source_pdf_pages"),
                "raw_source_text_sha256": n.get("raw_source_text_sha256") or n.get("raw_text_sha256"),
                "validation_flags": n.get("validation_flags"),
            })
        return {"run_id": run_id, "nodes": out, "boundary": BOUNDARY, "agent_bindable": True}

    def get_source_node(self, run_id: str, node_id: str, purpose: str = "") -> Dict[str, Any]:
        g = self._guard(run_id)
        self._log("get_source_node", run_id, [node_id], purpose, "ok" if g.get("ok") else "blocked")
        if not g.get("ok") or not g["contract"].get("agent_bindable"):
            return {"agent_bindable": False, "block_reason": (g.get("error") or (g.get("contract") or {}).get("block_reason")), "boundary": BOUNDARY}
        nodes = json.loads((self.output_dir / "clause_ast.json").read_text(encoding="utf-8"))
        for n in nodes:
            if n.get("node_id") == node_id or n.get("clause_id") == node_id:
                return {"run_id": run_id, "node": n, "boundary": BOUNDARY, "agent_bindable": True}
        return {"error": "node_not_found", "node_id": node_id, "boundary": BOUNDARY}

    def get_evidence(self, run_id: str, node_id: str, purpose: str = "") -> Dict[str, Any]:
        g = self._guard(run_id)
        self._log("get_evidence", run_id, [node_id], purpose, "ok" if g.get("ok") else "blocked")
        if not g.get("ok") or not g["contract"].get("agent_bindable"):
            return {"agent_bindable": False, "block_reason": (g.get("error") or (g.get("contract") or {}).get("block_reason")), "boundary": BOUNDARY}
        path = self.output_dir / "source_evidence.jsonl"
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    rec = json.loads(line)
                    if rec.get("node_id") == node_id or rec.get("clause_id") == node_id:
                        return {"run_id": run_id, "evidence": rec, "boundary": BOUNDARY, "agent_bindable": True}
        node = self.get_source_node(run_id, node_id, purpose=purpose)
        return {"run_id": run_id, "evidence": node.get("node"), "boundary": BOUNDARY, "agent_bindable": True}

    def validate_run(self, run_id: str, purpose: str = "") -> Dict[str, Any]:
        g = self._guard(run_id)
        self._log("validate_run", run_id, [], purpose, "ok" if g.get("ok") else "blocked")
        if not g.get("ok"):
            return g
        results = json.loads((self.output_dir / "validation_results.json").read_text(encoding="utf-8"))
        return {"run_id": run_id, "validation": results, "boundary": BOUNDARY, "agent_bindable": g["contract"].get("agent_bindable", False)}


def write_agent_contract(out_dir: Path, payload: Dict[str, Any]) -> Path:
    payload = dict(payload)
    payload["boundary"] = BOUNDARY
    payload["methods"] = [
        "get_run_status", "get_source_manifest", "list_source_nodes",
        "get_source_node", "get_evidence", "validate_run",
    ]
    payload["writes_allowed"] = False
    payload["external_actions_allowed"] = False
    path = out_dir / "agent_contract.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
