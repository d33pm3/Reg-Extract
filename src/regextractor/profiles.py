from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .paths import package_root


def load_profiles() -> List[Dict[str, Any]]:
    folder = package_root() / "config" / "profiles"
    if not folder.exists():
        return []
    out = []
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data["_path"] = str(path)
        out.append(data)
    return out


def select_profile(source_pdf: Optional[Path]) -> Dict[str, Any]:
    profiles = load_profiles()
    if source_pdf is None:
        return next((p for p in profiles if p.get("profile_id") == "generic"), {"profile_id": "generic", "validation_clauses": []})
    name = source_pdf.name
    digest = hashlib.sha256(source_pdf.read_bytes()).hexdigest() if source_pdf.exists() else ""
    for p in profiles:
        match = p.get("match") or {}
        sha = match.get("sha256")
        if sha and sha == digest:
            return p
        for token in match.get("filename_contains") or []:
            if token and token.lower() in name.lower():
                return p
    return next((p for p in profiles if p.get("profile_id") == "generic"), {"profile_id": "generic", "validation_clauses": []})


def clause_ids_for(profile: Dict[str, Any], discovered_ids: Optional[List[str]] = None) -> List[str]:
    declared = [str(c["id"]) for c in (profile.get("validation_clauses") or []) if c.get("id")]
    if declared:
        return declared
    if discovered_ids:
        numeric = [i for i in discovered_ids if i.isdigit()]
        if not numeric:
            return discovered_ids[:2]
        return [numeric[0], numeric[-1]] if len(numeric) > 1 else numeric[:1]
    return []
