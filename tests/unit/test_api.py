"""HTTP API contract and boundary checks (no services needed)."""

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _gen_contract():
    spec = importlib.util.spec_from_file_location("gen", ROOT / "tools" / "gen_api_contract.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_openapi_contract_is_fresh() -> None:
    gen = _gen_contract()
    assert gen.CONTRACT.read_text() == gen.render(), (
        "contracts/openapi.json is stale: run `uv run python tools/gen_api_contract.py` "
        "and `pnpm -C web gen:api`"
    )


def test_unknown_demo_user_is_rejected() -> None:
    from sdlcrag.api.main import app

    response = TestClient(app).get("/api/landscape", headers={"X-Demo-User": "mallory"})
    assert response.status_code == 403


def test_languages_stay_on_their_side_of_the_boundary() -> None:
    """TypeScript/JavaScript only in web/, Python never in web/ (ADR-0019)."""
    stray_ts = [p for p in (ROOT / "src").rglob("*") if p.suffix in {".ts", ".tsx", ".js", ".jsx"}]
    stray_py = [p for p in (ROOT / "web").rglob("*.py") if "node_modules" not in p.parts]
    assert not stray_ts, f"TypeScript/JavaScript outside web/: {stray_ts}"
    assert not stray_py, f"Python inside web/: {stray_py}"
