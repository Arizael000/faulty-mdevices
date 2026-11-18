"""Automated data-quality checks.

The pipeline runs these checks after cleaning and merging, and the dashboard
shows the results in its "Data quality" panel. They are intentionally simple
and explainable: uniqueness, completeness, allowed values, join coverage and
report consistency.
"""

from __future__ import annotations

import pandas as pd

from .utils import to_python_float, to_python_int

ALLOWED_RISK = {"1", "2", "3", "HDE", "Unclassified"}
ALLOWED_IMPLANTED = {"YES", "NO"}


def _check(checks: list[dict], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def validate_tables(
    devices: pd.DataFrame,
    events: pd.DataFrame,
    manufacturers: pd.DataFrame,
    enriched: pd.DataFrame,
    reports: dict[str, dict],
    merge_report: dict,
) -> dict:
    """Run and return a JSON-serialisable validation report."""
    checks: list[dict] = []

    for name, frame in (
        ("devices", devices),
        ("events", events),
        ("manufacturers", manufacturers),
    ):
        if "id" not in frame.columns:
            _check(checks, f"{name}.id exists", False, "id column is missing")
            continue
        duplicates = to_python_int(frame["id"].duplicated().sum())
        _check(
            checks,
            f"{name}.id is unique",
            duplicates == 0,
            f"{duplicates} duplicated ids out of {len(frame):,} rows",
        )

    device_nulls = to_python_int(devices.isna().sum().sum())
    _check(
        checks,
        "devices table is complete",
        device_nulls == 0,
        f"{device_nulls} missing cells after the complete-case filter",
    )

    manufacturer_names = to_python_int(manufacturers["name"].isna().sum())
    _check(
        checks,
        "manufacturers.name is populated",
        manufacturer_names == 0,
        f"{manufacturer_names} rows without a manufacturer name",
    )

    risk_values = set(devices["risk_class"].dropna().astype(str).str.strip())
    invalid_risk = sorted(risk_values - ALLOWED_RISK)
    _check(
        checks,
        "risk_class uses allowed values",
        not invalid_risk,
        "values: " + (", ".join(invalid_risk) if invalid_risk else "Class 1-3, HDE, Unclassified"),
    )

    implanted_values = set(devices["implanted"].dropna().astype(str).str.strip())
    invalid_implanted = sorted(implanted_values - ALLOWED_IMPLANTED)
    _check(
        checks,
        "implanted uses YES/NO",
        not invalid_implanted,
        "values: " + (", ".join(invalid_implanted) if invalid_implanted else "YES, NO"),
    )

    if "date_initiated_by_firm" in events.columns:
        parsed = to_python_float(events["date_initiated_by_firm"].notna().mean() * 100)
        _check(
            checks,
            "event dates are parsed",
            parsed >= 95.0,
            f"{parsed}% of cleaned events have a valid date",
        )

    events_total = to_python_int(merge_report.get("events_rows", len(enriched)))
    matched = to_python_int(merge_report.get("matched_rows", 0))
    coverage = round(matched / events_total * 100, 2) if events_total else 0.0
    _check(
        checks,
        "device join coverage >= 75%",
        coverage >= 75.0,
        f"{matched:,} of {events_total:,} recalls matched ({coverage}%)",
    )

    matched_rows = enriched[enriched.get("has_device", 0) == 1]
    missing_manufacturers = to_python_int(matched_rows["manufacturer_name"].isna().sum())
    _check(
        checks,
        "matched devices resolve a manufacturer",
        missing_manufacturers == 0,
        f"{missing_manufacturers} matched recalls without manufacturer",
    )

    duplicate_events = to_python_int(enriched["event_id"].duplicated().sum()) if "event_id" in enriched else -1
    _check(
        checks,
        "enriched event_id is unique",
        duplicate_events == 0,
        f"{duplicate_events} duplicated event ids",
    )

    if "event_country" in enriched.columns:
        missing_country = to_python_int(enriched["event_country"].isna().sum())
        _check(
            checks,
            "event_country is populated",
            missing_country == 0,
            f"{missing_country} recalls without a country",
        )

    consistent = (
        len(devices) == reports["devices"]["clean_rows"]
        and len(events) == reports["events"]["clean_rows"]
        and len(manufacturers) == reports["manufacturers"]["clean_rows"]
    )
    _check(
        checks,
        "clean row counts match the ETL report",
        consistent,
        "devices, events and manufacturers reports agree with the dataframes",
    )

    passed = sum(1 for check in checks if check["ok"])
    return {
        "checks": checks,
        "passed": to_python_int(passed),
        "failed": to_python_int(len(checks) - passed),
        "total": to_python_int(len(checks)),
    }
