#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/strip-ai.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp "$here/strip_ai.py" "$here"/cleanup_*.py "$work/"

for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    PYTHONIOENCODING=utf-8 "$py" -I -c 'import runpy, sys; directory = sys.argv.pop(1); sys.path.insert(0, directory); sys.argv[0] = directory + "/strip_ai.py"; runpy.run_path(sys.argv[0], run_name="__main__")' "$work" "$@"
    exit
  fi
done
printf 'strip-ai: Python 3.10+ is required\n' >&2
exit 2
