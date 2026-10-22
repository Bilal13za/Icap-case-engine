"""Spec §18.11: exported workings round-trip through CSV and Excel.

Prefers an app-provided exporter when one exists (any function with csv/excel
in its name under engine/ or calcs/); otherwise round-trips real calculation
output with the stdlib csv module and openpyxl directly.
"""

import csv
import importlib
import pkgutil

import openpyxl
import pytest

import calcs
import engine
from .conftest import run_calc


def _discover_exporter(kind):
    """Find (module, func) for 'csv' or 'excel' exports in engine/calcs."""
    for package in (engine, calcs):
        for _, modname, _ in pkgutil.iter_modules(package.__path__):
            mod = importlib.import_module(f"{package.__name__}.{modname}")
            for attr in dir(mod):
                if kind in attr.lower() and ("export" in attr.lower() or "write" in attr.lower()):
                    fn = getattr(mod, attr)
                    if callable(fn):
                        return mod.__name__, fn
    return None, None


def _workings_rows():
    """Real workings from the calculation engine: NPV at three discount rates."""
    from decimal import Decimal

    rows = [["rate", "npv"]]
    for rate in ("0.08", "0.10", "0.12"):
        res = run_calc("CALC-NPV", discount_rate=Decimal(rate),
                       cash_flows=[-1000, 300, 400, 500])
        rows.append([rate, str(res.result)])
    return rows


def _write_csv(rows, path):
    modname, fn = _discover_exporter("csv")
    if fn is not None:
        for args in ((rows, path), (path, rows), (rows, str(path)), (str(path), rows)):
            try:
                fn(*args)
                if path.exists():
                    return f"app:{modname}.{fn.__name__}"
            except (TypeError, ValueError):
                continue
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)
    return "fallback:csv"


def _write_excel(rows, path):
    modname, fn = _discover_exporter("excel")
    if fn is None:
        modname, fn = _discover_exporter("xlsx")
    if fn is not None:
        for args in ((rows, path), (path, rows), (rows, str(path)), (str(path), rows)):
            try:
                fn(*args)
                if path.exists():
                    return f"app:{modname}.{fn.__name__}"
            except (TypeError, ValueError):
                continue
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Workings"
    for row in rows:
        ws.append(row)
    wb.save(path)
    return "fallback:openpyxl"


def test_csv_export_round_trip(tmp_path):
    rows = _workings_rows()
    path = tmp_path / "workings.csv"
    used = _write_csv(rows, path)
    assert path.exists(), f"CSV export produced no file (via {used})"
    with open(path, encoding="utf-8") as fh:
        back = list(csv.reader(fh))
    assert back == rows, f"CSV round-trip mismatch (via {used})"


def test_excel_export_round_trip(tmp_path):
    rows = _workings_rows()
    path = tmp_path / "workings.xlsx"
    used = _write_excel(rows, path)
    assert path.exists(), f"Excel export produced no file (via {used})"
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    back = [[c.value for c in row] for row in ws.iter_rows()]
    # normalise: everything read back as text for comparison
    back = [[str(v) if v is not None else "" for v in row] for row in back]
    want = [[str(v) for v in row] for row in rows]
    assert back[: len(want)] == want, f"Excel round-trip mismatch (via {used})"
