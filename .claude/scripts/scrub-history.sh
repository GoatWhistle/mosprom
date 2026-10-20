#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
here=$(cd "$(dirname "$0")" && pwd)
src=${1:-$root}
if [[ $# -gt 2 ]]; then
  printf 'usage: scrub-history.sh [source [output]]\n' >&2
  exit 2
fi
if [[ $# -eq 2 ]]; then
  bash "$here/strip-ai.sh" --export "$src" "$2"
else
  bash "$here/strip-ai.sh" --export "$src"
fi
