#!/usr/bin/env bash
# Fails if a tracked file matches a pattern from the maintainer's local, untracked list
# (.git/info/forbidden-words, one extended regex per line). No list, no check.
set -euo pipefail
list="$(git rev-parse --git-dir)/info/forbidden-words"
[[ -s "$list" ]] || exit 0
if git grep -Iin -E -f "$list" -- . ; then
  echo "forbidden wording found (patterns: $list)" >&2
  exit 1
fi
