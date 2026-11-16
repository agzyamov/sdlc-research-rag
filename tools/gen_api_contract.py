"""Write the HTTP contract (contracts/openapi.json) from the FastAPI app (ADR-0019).

The web app's TypeScript types are generated from this file (`pnpm -C web gen:api`), so the
Python response models are the single source of truth for the Python/TypeScript boundary.
Run after changing `sdlcrag.api`; pytest and CI fail when the file is stale.
"""

import json
from pathlib import Path

from sdlcrag.api.main import app

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    CONTRACT.write_text(render())
    print(f"wrote {CONTRACT}")
