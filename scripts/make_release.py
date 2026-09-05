#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", "work", "output", "dist", ".venv", "venv"}
SKIP_SUFFIX = {".pyc", ".pdf", ".tmp", ".pem", ".key"}


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.suffix in SKIP_SUFFIX:
            continue
        yield path, rel


def main() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    files = {}
    h = hashlib.sha256()
    for path, rel in sorted(iter_files(), key=lambda x: str(x[1])):
        key = str(rel).replace("\\", "/")
        if key == "RELEASE_MANIFEST.json":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files[key] = digest
        h.update(digest.encode())
        h.update(key.encode())
    release_hash = h.hexdigest()
    manifest = {
        "name": "RegExtractor",
        "version": version,
        "release_hash": release_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_source": "https://github.com/d33pm3/Reg-Extract",
        "runtime_github_required": False,
        "file_hashes": files,
    }
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    zip_path = dist / f"RegExtractor-Grok-{version}.zip"
    skill_zip = dist / f"RegExtractor-Grok-skill-{version}.zip"
    include_prefix = ["VERSION", "RELEASE_MANIFEST.json", "requirements.lock", "SKILL.md", "README.md", "pyproject.toml", "pytest.ini", "config", "src", "scripts", "tests", "references", ".github", ".gitignore"]

    def wanted(rel: Path) -> bool:
        s = str(rel).replace("\\", "/")
        return any(s == p or s.startswith(p + "/") for p in include_prefix)

    for dest in (zip_path, skill_zip):
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, rel in sorted(iter_files(), key=lambda x: str(x[1])):
                if wanted(rel):
                    zf.write(path, str(rel))
    claude = dist / f"RegExtractor-Claude-{version}.zip"
    shutil.copy2(zip_path, claude)
    sums = dist / "SHA256SUMS.txt"
    lines = []
    for dest in (zip_path, skill_zip, claude):
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        lines.append(f"{digest}  {dest.name}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(version)
    print(release_hash)
    print(zip_path)
    print(skill_zip)
    print(sums)


if __name__ == "__main__":
    main()
