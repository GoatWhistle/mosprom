#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"

skills=()
for skill in skills/*/; do
  [[ -f $skill/SKILL.md ]] || continue
  skills+=("$(basename "$skill")")
done
[[ ${#skills[@]} -gt 0 ]] || { echo "no skills found in skills/" >&2; exit 1; }

for destination in .claude/skills .agents/skills; do
  [[ ! -L $destination ]] || { echo "expected a directory: $destination" >&2; exit 1; }
  for name in "${skills[@]}"; do
    link=$destination/$name
    target=../../skills/$name
    if [[ -e $link || -L $link ]]; then
      if [[ ! -L $link || $(readlink "$link") != "$target" ]]; then
        echo "refusing to replace an existing skill: $link" >&2
        exit 1
      fi
    fi
  done
done

for destination in .claude/skills .agents/skills; do
  mkdir -p "$destination"
  for link in "$destination"/*; do
    [[ -L $link ]] || continue
    target=$(readlink "$link")
    if [[ $target == ../../skills/* && ! -f $link/SKILL.md ]]; then
      rm "$link"
    fi
  done
  for name in "${skills[@]}"; do
    link=$destination/$name
    [[ -L $link ]] || ln -s "../../skills/$name" "$link"
  done
  printf '%s: %d links to skills/\n' "$destination" "${#skills[@]}"
done
