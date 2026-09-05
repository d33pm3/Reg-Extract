#!/usr/bin/env python3
"""Blocking smoke test for Clause 129 and Clause 358 against a source PDF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regextractor.cli import run_smoke  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("--out", default="work/smoke_test")
    p.add_argument("--clauses", nargs="+", default=["129", "358"])
    args = p.parse_args()
    return run_smoke(Path(args.source), Path(args.out), list(args.clauses))


if __name__ == "__main__":
    raise SystemExit(main())
