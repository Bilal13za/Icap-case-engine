"""Spec §18.12: offline operation.

1. Static: engine/, calcs/, dbcore.py and seed.py contain no network imports or
   network-call sites (AST-based, so URLs in comments/docstrings don't trip it).
2. Functional: with the socket layer blocked, rule evaluation, framework
   selection, calculations and DB reads all still work.
"""

import ast
import socket
from decimal import Decimal
from pathlib import Path

import pytest

from .conftest import (
    ROOT,
    decision_types,
    find_rule,
    run_calc,
)

NETWORK_MODULES = {
    "socket", "ssl", "urllib", "urllib3", "requests", "httpx", "aiohttp",
    "http", "ftplib", "smtplib", "imaplib", "poplib", "telnetlib",
    "websocket", "websockets",
}


def _scan_file(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in NETWORK_MODULES:
                    hits.append(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in NETWORK_MODULES:
                hits.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name in {"urlopen", "create_connection", "getaddrinfo"}:
                hits.append(f"call {name}()")
    return hits


def _python_files():
    files = [ROOT / "dbcore.py", ROOT / "seed.py"]
    for pkg in ("engine", "calcs"):
        pkgdir = ROOT / pkg
        if pkgdir.is_dir():
            files.extend(p for p in pkgdir.rglob("*.py") if "__pycache__" not in str(p))
    return files


def test_no_network_imports_in_engine_calcs_dbcore():
    offenders = {}
    for path in _python_files():
        hits = _scan_file(path)
        if hits:
            offenders[str(path.relative_to(ROOT))] = hits
    assert not offenders, f"network imports/calls found: {offenders}"


@pytest.fixture()
def no_network(monkeypatch):
    def _blocked(*a, **k):
        raise AssertionError("network access attempted — engine must be offline")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    return True


def test_engine_works_with_sockets_blocked(no_network, conn):
    from engine.frameworks import recommend_frameworks
    from engine.rules import evaluate_rules, load_rules

    rules = load_rules()
    rule = find_rule(rules, "working", "capital")
    from .conftest import facts_firing

    matches = evaluate_rules(facts_firing(rule), rules)
    assert rule["rule_id"] in [m.rule_id for m in matches]

    dts = decision_types()
    recs = recommend_frameworks(dts[0], [])
    assert recs

    res = run_calc("CALC-NPV", discount_rate=Decimal("0.10"),
                   cash_flows=[-1000, 300, 400, 500])
    assert res.result == Decimal("-21.03")

    n = conn.execute("SELECT COUNT(*) AS n FROM TriggerRules").fetchone()["n"]
    assert n == 30


def test_recommendation_works_with_sockets_blocked(no_network):
    from .conftest import call_build_recommendation

    assert call_build_recommendation() is not None
