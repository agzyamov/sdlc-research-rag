#!/usr/bin/env bash
# Validate every Mermaid block in the docs by rendering it with mermaid-cli.
# Fails on any syntax error. The rendered output goes to a temp dir and is discarded.
set -euo pipefail
MMDC_VERSION="12.2.0"
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

status=0
while IFS= read -r f; do
  out="$tmp/$(echo "$f" | tr '/' '_')"
  # --no-sandbox only matters in CI containers (Ubuntu restricts Chrome sandboxing there)
  if npx -y "@mermaid-js/mermaid-cli@${MMDC_VERSION}" -q -p tools/puppeteer-config.json -i "$f" -o "$out" >"$tmp/log" 2>&1; then
    echo "ok   $f"
  else
    echo "FAIL $f"; cat "$tmp/log"; status=1
  fi
done < <(grep -rl --include='*.md' '```mermaid' docs README.md 2>/dev/null || true)
exit $status
