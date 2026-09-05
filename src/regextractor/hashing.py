from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def config_hash(payload: dict) -> str:
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def run_id(source_sha: str, cfg_sha: str, release_sha: str) -> str:
    return sha256_text(f"{source_sha}|{cfg_sha}|{release_sha}")


def write_sha256_manifest(out_dir: Path) -> Path:
    lines = []
    for path in sorted(out_dir.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        lines.append(f"{sha256_file(path)}  {path.name}")
    dest = out_dir / "MANIFEST.sha256"
    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return dest
