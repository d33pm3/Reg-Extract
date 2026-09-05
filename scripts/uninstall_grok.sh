#!/usr/bin/env bash
# Remove only the RegExtractor skill directory.
set -euo pipefail
TARGET="${1:-/home/workdir/.grok/skills/regextractor}"
if [[ ! -d "$TARGET" ]]; then
  echo "NOT_INSTALLED $TARGET"
  exit 0
fi
if [[ ! -f "$TARGET/SKILL.md" ]] || ! grep -q "name: regextractor" "$TARGET/SKILL.md"; then
  echo "REFUSING_UNRELATED_PATH $TARGET"
  exit 2
fi
rm -rf "$TARGET"
echo "REMOVED $TARGET"
