from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    """Skill/repo root containing VERSION, config/, src/."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "VERSION").exists() and (parent / "src").exists():
            return parent
    return here.parents[2]


def version() -> str:
    p = package_root() / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "0.0.0-dev"
