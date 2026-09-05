#!/usr/bin/env bash
set -euo pipefail
SELF="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_ROOT="$(cd "$SELF/.." && pwd)"
SRC="${1:-$DEFAULT_ROOT}"
TARGET="${2:-/home/workdir/.grok/skills/regextractor}"
WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT
if [[ -f "$SRC" && "$SRC" == *.zip ]]; then
  python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$SRC" "$WORKDIR"
  if [[ -f "$WORKDIR/SKILL.md" ]]; then ROOT="$WORKDIR"
  elif [[ -f "$WORKDIR/RegExtractor/SKILL.md" ]]; then ROOT="$WORKDIR/RegExtractor"
  else ROOT="$(python3 -c "from pathlib import Path; hits=list(Path('$WORKDIR').rglob('SKILL.md')); print(hits[0].parent if hits else '')")"
  fi
else
  ROOT="$SRC"
fi
test -n "$ROOT" && test -f "$ROOT/SKILL.md" && test -f "$ROOT/VERSION"
grep -q "name: regextractor" "$ROOT/SKILL.md"
if [[ -d "$TARGET" && -f "$TARGET/SKILL.md" ]]; then
  if ! grep -q "name: regextractor" "$TARGET/SKILL.md"; then
    echo "REFUSING_UNRELATED_TARGET $TARGET"
    exit 2
  fi
fi
mkdir -p "$TARGET"
python3 - "$ROOT" "$TARGET" <<'PY'
import shutil, sys
from pathlib import Path
root = Path(sys.argv[1]); target = Path(sys.argv[2])
skip = {".git", ".pytest_cache", "__pycache__", "dist", "work", "output"}
if target.exists():
    for child in list(target.iterdir()):
        if child.is_dir(): shutil.rmtree(child)
        else: child.unlink()
n = 0
for src in root.rglob("*"):
    if not src.is_file(): continue
    rel = src.relative_to(root)
    if any(part in skip for part in rel.parts): continue
    dest = target / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest); n += 1
print("copied", n, "files")
print("version", (target / "VERSION").read_text(encoding="utf-8").strip())
PY
echo "INSTALLED $TARGET"
echo "DISCOVERY_FILE=$TARGET/SKILL.md"
