#!/usr/bin/env bash
set -euo pipefail

dry=0
if [[ ${1:-} == --dry-run ]]; then dry=1; shift; fi
if [[ $# -lt 2 ]]; then
  echo "usage: run-worker.sh [--dry-run] <N> <slug> [part line]" >&2
  exit 2
fi
n=$1 slug=$2 part=${3:-}

root=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)
wt=$root/.claude/worktrees/$slug
log=$root/.claude/worktrees/logs/$slug.log

prompt="You work autonomously in your own worktree, nobody will answer. Ask questions as an issue comment with options,
  take the recommended option and continue. When the work is done, open and merge the PR. /implement $n"
if [[ -n $part ]]; then prompt+=$'\n'"$part"; fi

run() {
  if (( dry )); then printf '+ %q' "$1"; shift; printf ' %q' "$@"; echo; else "$@"; fi
}

run git -C "$root" fetch -q origin
if [[ -d $wt ]]; then
  echo "worktree $wt exists, continuing in it"
elif git -C "$root" show-ref -q --verify "refs/heads/feat/$slug"; then
  run git -C "$root" worktree add -q "$wt" "feat/$slug"
else
  run git -C "$root" worktree add -q -b "feat/$slug" "$wt" origin/main
fi
run mkdir -p "$(dirname "$log")"

if (( dry )); then
  echo "+ cd $wt && claude -p <prompt> --model ${MODEL:-opus} --permission-mode bypassPermissions >> $log 2>&1"
  echo "--- prompt"
  echo "$prompt"
  exit 0
fi

printf '\n===== %s run #%s\n' "$(date -u +%FT%TZ)" "$n" >> "$log"
(cd "$wt" && claude -p "$prompt" --model "${MODEL:-opus}" --permission-mode bypassPermissions) >> "$log" 2>&1 || true
echo "#$n $slug: worker finished, log $log"
