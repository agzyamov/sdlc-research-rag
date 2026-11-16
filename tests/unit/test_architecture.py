"""Architecture conformance: the code must match the Views and Beyond documentation."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "sdlcrag"
DOCS = ROOT / "docs" / "architecture"


def _code_packages() -> set[str]:
    pkgs = {p.parent.relative_to(SRC.parent) for p in SRC.rglob("__init__.py")}
    return {".".join(p.parts) for p in pkgs if p.parts != ("sdlcrag",)}


def _documented(doc: str) -> set[str]:
    text = (DOCS / doc).read_text(encoding="utf-8")
    return set(re.findall(r"`(sdlcrag\.[a-z_.]+)`", text))


def test_import_linter_contracts_pass() -> None:
    """Module View uses-rules (layers) hold in the code."""
    result = subprocess.run(
        [sys.executable, "-m", "importlinter.cli"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_package_is_in_module_view() -> None:
    assert _code_packages() <= _documented("01-module-view.md"), (
        "Package(s) not in the Module View. Escalate for an architectural decision: "
        f"{_code_packages() - _documented('01-module-view.md')}"
    )


def test_module_view_and_allocation_view_agree() -> None:
    assert _documented("01-module-view.md") == _documented("03-allocation-view.md")


def test_every_module_view_element_is_implemented() -> None:
    assert _documented("01-module-view.md") <= _code_packages()


def test_generated_diagrams_are_fresh() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_diagrams.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
