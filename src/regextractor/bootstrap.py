from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

from .paths import package_root


def missing_mandatory() -> List[str]:
    missing = []
    for name in ("pydantic", "pdfplumber", "pypdf", "yaml"):
        try:
            __import__(name if name != "yaml" else "yaml")
        except Exception:
            missing.append("PyYAML" if name == "yaml" else name)
    return missing


def try_install() -> dict:
    root = package_root()
    lock = root / "requirements.lock"
    if not lock.exists():
        return {"attempted": False, "ok": False, "error": "lockfile_missing"}
    missing = missing_mandatory()
    if not missing:
        return {"attempted": False, "ok": True, "installed": [], "note": "already_present"}
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(lock)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return {
            "attempted": True,
            "ok": proc.returncode == 0,
            "command": cmd,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    except Exception as exc:
        return {
            "attempted": True,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "note": "host_may_prohibit_installation",
        }
