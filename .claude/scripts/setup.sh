#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"

git config core.hooksPath .claude/git-hooks
chmod +x .claude/git-hooks/commit-msg .claude/git-hooks/pre-commit .claude/git-hooks/pre-push .claude/scripts/*.sh
find skills -path '*/scripts/*' -type f \
  \( -name '*.sh' -o -name impeccable \) -exec chmod +x {} +
bash .claude/scripts/sync-agents.sh

printf 'hooks: %s\n' "$(git config core.hooksPath)"
printf 'next: put the organizer materials into brief/, then run the hack-kickoff skill\n'
