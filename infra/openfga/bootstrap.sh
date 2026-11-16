#!/usr/bin/env bash
# Create the OpenFGA store (model + base tuples) with the official CLI and record its ids in .env.
# Idempotent: does nothing if SDLCRAG_OPENFGA_STORE_ID is already set (pass --force to recreate).
set -euo pipefail
cd "$(dirname "$0")/../.."
FGA_CLI="openfga/cli:v0.9.0"
NETWORK="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' "$(docker compose ps -q openfga)")"

current="$(grep -E '^SDLCRAG_OPENFGA_STORE_ID=.+' .env 2>/dev/null || true)"
if [[ -n "$current" && "${1:-}" != "--force" ]]; then
  echo "OpenFGA store already configured in .env (use --force to recreate)"; exit 0
fi

out="$(docker run --rm --network "$NETWORK" -v "$PWD/infra/openfga:/work" "$FGA_CLI" \
  store import --file /work/store.fga.yaml --api-url http://openfga:8080)"
store_id="$(echo "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["store"]["id"])')"
model_id="$(echo "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["model"]["authorization_model_id"])')"

python3 - "$store_id" "$model_id" <<'PY'
import re, sys
from pathlib import Path
store, model = sys.argv[1:3]
env = Path(".env")
text = env.read_text()
for key, value in (("SDLCRAG_OPENFGA_STORE_ID", store), ("SDLCRAG_OPENFGA_MODEL_ID", model)):
    line = f"{key}={value}"
    text = re.sub(rf"^{key}=.*$", line, text, flags=re.M) if re.search(rf"^{key}=", text, re.M) else text + line + "\n"
env.write_text(text)
PY
echo "OpenFGA store $store_id (model $model_id) written to .env"
