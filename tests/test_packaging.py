"""Packaging checks: required files exist, app.py compiles without a Streamlit
install, dependency pins and the Windows launcher reference the right names."""

import py_compile
from pathlib import Path

from .conftest import ROOT

REQUIRED_FILES = [
    "app.py",
    "seed.py",
    "dbcore.py",
    "requirements.txt",
    "run_windows.bat",
    "README.md",
    "BUILD_NOTES.md",
    "SYLLABUS_VERIFICATION.md",
    "db/schema.sql",
    "docs/VERIFICATION.md",
    "docs/ROADMAP.md",
    "data/syllabus.json",
    "data/frameworks.json",
    "data/rules.json",
    "data/cases.json",
    "data/questions.json",
    "data/formulas.json",
]


def test_required_files_present():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).exists()]
    assert not missing, f"missing required files: {missing}"


def test_app_compiles():
    # Must compile without streamlit installed — proves no import-time surprises
    # for the syntax check at least; the UI itself is exercised manually.
    py_compile.compile(str(ROOT / "app.py"), doraise=True)


def test_requirements_pins():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for dep in ("streamlit", "openpyxl", "pytest"):
        assert dep in text, f"{dep} missing from requirements.txt"
    assert "yaml" not in text, "PyYAML must not be a dependency (Windows C-extension risk)"


def test_windows_launcher_references():
    # v5 launcher: run_windows.bat is a thin stub; the boot logic lives in
    # launcher.ps1. The test guards the tokens in the file that has them,
    # and asserts the stub still delegates to the ps1.
    stub = (ROOT / "run_windows.bat").read_text(encoding="utf-8")
    assert "launcher.ps1" in stub, "run_windows.bat must delegate to launcher.ps1"
    text = (ROOT / "launcher.ps1").read_text(encoding="utf-8")
    for token in ("app.py", "seed.py", "case_engine.db", "LOCALAPPDATA", "streamlit"):
        assert token in text, f"launcher.ps1 does not mention {token}"


def test_decision_comparator_validates_weights():
    """§18.8 (static): the Decision Comparator in app.py requires user-entered
    weights summing to 100 and refuses to score otherwise — the app never
    invents weights. (Streamlit UI code is not imported in tests; this guards
    the validation logic against regression.)"""
    text = (ROOT / "app.py").read_text(encoding="utf-8").lower()
    assert "weights must sum to 100" in text
    assert "will not invent weights" in text
    # an actual numeric guard on the sum, not just prose
    import re

    assert re.search(r"abs\(.*weight_sum.*-\s*100\s*\)", text), (
        "no numeric weights-sum-to-100 guard found in app.py"
    )
