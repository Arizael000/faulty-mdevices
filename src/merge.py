"""Merge layer: events -> devices -> manufacturers.

The dashboard uses a *left* join so every recall stays visible. The subset
that also has a cleaned device record is flagged with ``has_device``.
"""

from __future__ import annotations

import pandas as pd

from .utils import to_python_float, to_python_int

EVENT_RENAMES = {
    "id": "event_id",
    "country": "event_country",
    "number": "event_number",
    "source": "event_source",
    "slug": "event_slug",
    "created_at": "event_created_at",
}

DEVICE_RENAMES = {
    "id": "device_key",
    "name": "device_name",
    "slug": "device_slug",
    "created_at": "device_created_at",
}

MANUFACTURER_RENAMES = {
    "id": "manufacturer_key",
    "name": "manufacturer_name",
    "slug": "manufacturer_slug",
    "source": "manufacturer_source",
    "created_at": "manufacturer_created_at",
}


def _rename(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    present = {old: new for old, new in mapping.items() if old in df.columns}
    return df.rename(columns=present)


def build_enriched(
    events: pd.DataFrame,
    devices: pd.DataFrame,
    manufacturers: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (left-joined enriched events, inner subset, merge report)."""
    events = _rename(events.copy(), EVENT_RENAMES)
    devices = _rename(devices.copy(), DEVICE_RENAMES)
    manufacturers = _rename(manufacturers.copy(), MANUFACTURER_RENAMES)

    enriched = events.merge(
        devices,
        left_on="device_id",
        right_on="device_key",
        how="left",
        suffixes=("", "_device"),
    )
    enriched = enriched.merge(
        manufacturers,
        left_on="manufacturer_id",
        right_on="manufacturer_key",
        how="left",
        suffixes=("", "_manufacturer"),
    )

    enriched["has_device"] = enriched["device_key"].notna().astype("int8")
    enriched = enriched.drop(columns=["device_key", "manufacturer_key"], errors="ignore")

    if "date_initiated_by_firm" in enriched.columns:
        enriched["date_initiated_by_firm"] = pd.to_datetime(
            enriched["date_initiated_by_firm"], errors="coerce", format="ISO8601"
        )
        enriched["year"] = enriched["date_initiated_by_firm"].dt.year
    else:
        enriched["year"] = pd.NA

    inner = enriched[enriched["has_device"] == 1].copy()

    matched = to_python_int(enriched["has_device"].sum())
    total = to_python_int(len(enriched))
    report = {
        "events_rows": total,
        "devices_rows": to_python_int(len(devices)),
        "manufacturers_rows": to_python_int(len(manufacturers)),
        "matched_rows": matched,
        "unmatched_rows": total - matched,
        "coverage_pct": round(matched / total * 100, 2) if total else 0.0,
        "inner_rows": to_python_int(len(inner)),
        "manufacturers_unmatched_inner": to_python_int(
            inner["manufacturer_name"].isna().sum()
        ),
        "date_min": _date(enriched["date_initiated_by_firm"].min()),
        "date_max": _date(enriched["date_initiated_by_firm"].max()),
    }
    return enriched, inner, report


def _date(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(pd.Timestamp(value).date())


def load_enriched(path) -> tuple[pd.DataFrame, dict]:
    """Load a previously generated enriched CSV (``--skip-etl`` mode)."""
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    if "date_initiated_by_firm" in df.columns:
        df["date_initiated_by_firm"] = pd.to_datetime(
            df["date_initiated_by_firm"], errors="coerce", format="ISO8601"
        )
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    total = len(df)
    matched = int(df["has_device"].fillna(0).sum()) if "has_device" in df else 0
    report = {
        "events_rows": total,
        "matched_rows": matched,
        "unmatched_rows": total - matched,
        "coverage_pct": round(matched / total * 100, 2) if total else 0.0,
        "inner_rows": matched,
        "loaded_from_csv": True,
    }
    return df, report


def coverage_fraction(enriched: pd.DataFrame) -> float:
    """Share of recalls that could be linked to a cleaned device record."""
    if len(enriched) == 0:
        return 0.0
    return to_python_float(enriched["has_device"].mean() * 100)
