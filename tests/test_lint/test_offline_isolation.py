"""The lint core must be importable, deterministic, and fully offline.

These tests guard the architectural contract: ``skill_refine.lint`` must never
pull in an LLM/provider/network dependency (httpx, anthropic, skill_refine.llm).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import skill_refine.lint

# Import-statement forms only, so docstrings that merely *mention* the LLM
# layer (e.g. "lives in skill_refine.llm.models") are not false positives.
_FORBIDDEN_SOURCE_TOKENS = (
    "import httpx",
    "from httpx",
    "import anthropic",
    "from anthropic",
    "import skill_refine.llm",
    "from skill_refine.llm",
    "import skill_refine.providers",
    "from skill_refine.providers",
)


def test_lint_import_pulls_no_llm_or_network_modules() -> None:
    """Import the whole lint package in a clean interpreter and inspect sys.modules."""
    code = (
        "import importlib, pkgutil\n"
        "import skill_refine.lint as L\n"
        "for m in pkgutil.iter_modules(L.__path__):\n"
        "    importlib.import_module('skill_refine.lint.' + m.name)\n"
        "import sys\n"
        "bad = [n for n in sys.modules\n"
        "       if n.split('.')[0] in {'httpx', 'anthropic'}\n"
        "       or n.startswith('skill_refine.llm')]\n"
        "assert not bad, 'lint imported forbidden modules: %r' % bad\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_lint_sources_have_no_forbidden_imports() -> None:
    root = Path(skill_refine.lint.__file__).parent
    offenders: list[str] = []
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for token in _FORBIDDEN_SOURCE_TOKENS:
            if token in text:
                offenders.append(f"{py.name}: {token}")
    assert not offenders, offenders
