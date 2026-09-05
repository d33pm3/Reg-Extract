from __future__ import annotations

import zipfile
from pathlib import Path
from typing import List

MAX_MEMBER_BYTES = 50 * 1024 * 1024


class UnsafeArchiveError(ValueError):
    pass


def validate_zip_members(zf: zipfile.ZipFile) -> List[str]:
    names = []
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or name.startswith("\\"):
            raise UnsafeArchiveError(f"absolute_path:{name}")
        if ".." in Path(name).parts:
            raise UnsafeArchiveError(f"path_traversal:{name}")
        if info.is_dir():
            continue
        if info.file_size > MAX_MEMBER_BYTES:
            raise UnsafeArchiveError(f"oversized:{name}:{info.file_size}")
        if info.external_attr >> 16 & 0o170000 == 0o120000:
            raise UnsafeArchiveError(f"symlink:{name}")
        names.append(name)
    return names


def safe_extract(zip_path: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        validate_zip_members(zf)
        zf.extractall(dest)
    if (dest / "SKILL.md").exists():
        return dest
    hits = list(dest.rglob("SKILL.md"))
    if hits:
        return hits[0].parent
    raise UnsafeArchiveError("skill_identity_missing")


def expected_skill_identity(root: Path) -> bool:
    skill = root / "SKILL.md"
    if not skill.exists():
        return False
    text = skill.read_text(encoding="utf-8", errors="replace")
    return "name: regextractor" in text and (root / "VERSION").exists()
