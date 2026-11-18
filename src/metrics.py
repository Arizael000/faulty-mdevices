"""Metrics layer.

Turns the enriched recall table into a compact, pre-aggregated cube that the
static dashboard can filter in the browser without shipping the raw CSVs.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd

from .config import get_category_cardinality, get_top_dim_values
from .utils import to_python_int

COUNTRY_NAMES = {
    "USA": "United States",
    "AUS": "Australia",
    "GBR": "United Kingdom",
    "IND": "India",
    "CAN": "Canada",
    "DEU": "Germany",
    "CHE": "Switzerland",
    "IRL": "Ireland",
    "ESP": "Spain",
    "FRA": "France",
    "SWE": "Sweden",
}

RISK_ORDER = {"1": 0, "2": 1, "3": 2, "HDE": 3, "UNCLASSIFIED": 4}

FACT_SCHEMA = [
    "year",
    "country",
    "risk_class",
    "implanted",
    "classification",
    "cause",
    "manufacturer",
    "device",
    "distribution",
    "has_device",
    "count",
]

DISTRIBUTION_LABELS = [
    "Unknown",
    "Nationwide",
    "Worldwide / international",
    "Nationwide + international",
    "Regional / local / other",
]


def _text(series: pd.Series) -> pd.Series:
    values = series.astype("object").astype(str).str.strip()
    return values.replace({"nan": "", "None": "", "none": "", "null": ""})


def _small_dim(series: pd.Series, display=None, order=None) -> dict:
    """Dimension with every distinct value kept."""
    values = _text(series)
    unique = [v for v in values.unique() if v != ""]
    if order is not None:
        unique = sorted(unique, key=lambda v: order.get(str(v).upper(), 99))
    else:
        unique = sorted(unique)

    mapping = {value: index + 1 for index, value in enumerate(unique)}
    indices = values.map(lambda v: mapping.get(v, 0)).astype(int)
    labels = ["Unknown"] + [display(v) if display else v for v in unique]
    return {"values": labels, "indices": indices, "_mapping": mapping}


def _top_dim(series: pd.Series, limit: int | None = None) -> dict:
    """Keep the top values and fold the long tail into ``Other (grouped)``."""
    if limit is None:
        limit = get_top_dim_values()
    values = _text(series)
    counts = values[values != ""].value_counts()
    top = counts.head(limit).index.tolist()
    other_index = len(top) + 1
    mapping = {value: index + 1 for index, value in enumerate(top)}
    indices = values.map(
        lambda v: 0 if v == "" else mapping.get(v, other_index)
    ).astype(int)
    labels = ["Unknown", *top, "Other (grouped)"]
    return {"values": labels, "indices": indices, "_mapping": mapping}


def _clean_device_names(series: pd.Series) -> pd.Series:
    values = _text(series)
    values = values.str.replace(r"^\s*Device\s+Recall\s*", "", regex=True, case=False)
    values = values.str.replace(r"\s+", " ", regex=True).str.strip()
    return values


def _distribution_index(series: pd.Series) -> pd.Series:
    """Normalise the free-text ``distributed_to`` field into four scopes.

    The raw field has >11,000 distinct strings; rule-based normalisation makes
    the "where was it distributed" question answerable in the dashboard.
    """
    values = _text(series).str.lower()

    def classify(value: str) -> int:
        if not value:
            return 0
        nationwide = bool(
            re.search(r"nation\s*-?\s*wide|all 50 states|all states", value)
        )
        worldwide = bool(re.search(r"world\s*-?\s*wide|international|global", value))
        if nationwide and worldwide:
            return 3
        if worldwide:
            return 2
        if nationwide:
            return 1
        return 4

    return values.map(classify).astype(int)


def _year_index(enriched: pd.DataFrame) -> pd.Series:
    if "year" in enriched.columns:
        years = pd.to_numeric(enriched["year"], errors="coerce").fillna(0).astype(int)
    elif "date_initiated_by_firm" in enriched.columns:
        years = (
            enriched["date_initiated_by_firm"]
            .dt.year.fillna(0)
            .astype(int)
        )
    else:
        years = pd.Series(0, index=enriched.index, dtype=int)
    return years.astype(int)


def build_metrics(enriched: pd.DataFrame, etl_report: dict) -> dict:
    """Build the JSON-serialisable object embedded in ``dashboard/app.js``."""
    years = _year_index(enriched)
    year_values = [0, *sorted(int(y) for y in years.unique() if int(y) > 0)]

    risk = _small_dim(enriched.get("risk_class", pd.Series(index=enriched.index)), order=RISK_ORDER)
    risk["values"] = ["Unknown"] + [
        f"Class {v}" if str(v) in {"1", "2", "3"} else str(v)
        for v in risk["values"][1:]
    ]

    implanted = _small_dim(
        enriched.get("implanted", pd.Series(index=enriched.index)),
        display=lambda v: v.capitalize(),
        order={"YES": 0, "NO": 1},
    )

    classification = _top_dim(
        enriched.get("classification", pd.Series(index=enriched.index))
    )
    cause = _top_dim(enriched.get("determined_cause", pd.Series(index=enriched.index)))
    manufacturer = _top_dim(
        enriched.get("manufacturer_name", pd.Series(index=enriched.index))
    )
    device = _top_dim(_clean_device_names(enriched.get("device_name", pd.Series(index=enriched.index))))
    distribution = _distribution_index(
        enriched.get("distributed_to", pd.Series(index=enriched.index))
    )

    country = _small_dim(
        enriched.get("event_country", pd.Series(index=enriched.index)),
        display=lambda v: COUNTRY_NAMES.get(v, v),
    )

    work = pd.DataFrame(
        {
            "year": years.map({value: index for index, value in enumerate(year_values)}),
            "country": country["indices"],
            "risk_class": risk["indices"],
            "implanted": implanted["indices"],
            "classification": classification["indices"],
            "cause": cause["indices"],
            "manufacturer": manufacturer["indices"],
            "device": device["indices"],
            "distribution": distribution,
            "has_device": pd.to_numeric(
                enriched.get("has_device", pd.Series(0, index=enriched.index)),
                errors="coerce",
            )
            .fillna(0)
            .astype(int),
        }
    )

    grouped = (
        work.groupby(FACT_SCHEMA[:-1], sort=True)
        .size()
        .reset_index(name="count")
    )
    facts = grouped[FACT_SCHEMA].astype(int).values.tolist()

    total_events = to_python_int(len(enriched))
    matched = to_python_int(work["has_device"].sum())
    date_series = enriched.get("date_initiated_by_firm")

    meta = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "dataset": "ICIJ Faulty Medical Devices Global Dataset",
        "total_events": total_events,
        "enriched_events": matched,
        "coverage_pct": round(matched / total_events * 100, 2) if total_events else 0.0,
        "date_min": _date_min(date_series),
        "date_max": _date_max(date_series),
        "fact_schema": FACT_SCHEMA,
        "etl": etl_report,
    }

    return {
        "meta": meta,
        "dims": {
            "years": year_values,
            "countries": country["values"],
            "riskClasses": risk["values"],
            "implanted": implanted["values"],
            "classifications": classification["values"],
            "causes": cause["values"],
            "manufacturers": manufacturer["values"],
            "devices": device["values"],
            "distributions": DISTRIBUTION_LABELS,
        },
        "facts": facts,
    }


def _date_min(series) -> str | None:
    if series is None:
        return None
    value = series.min()
    if pd.isna(value):
        return None
    return str(pd.Timestamp(value).date())


def _date_max(series) -> str | None:
    if series is None:
        return None
    value = series.max()
    if pd.isna(value):
        return None
    return str(pd.Timestamp(value).date())


def summarize(metrics: dict) -> str:
    """Human-readable summary printed by the pipeline."""
    meta = metrics["meta"]
    dims = metrics["dims"]
    lines = [
        f"Recalls (all):        {meta['total_events']:,}",
        f"Device-linked:        {meta['enriched_events']:,} ({meta['coverage_pct']}%)",
        f"Date range:           {meta['date_min']} -> {meta['date_max']}",
        f"Countries:            {len(dims['countries']) - 1}",
        f"Manufacturers (top):  {len(dims['manufacturers']) - 2} + grouped tail",
        f"Devices (top):        {len(dims['devices']) - 2} + grouped tail",
        f"Fact rows:            {len(metrics['facts']):,}",
    ]
    return "\n".join(lines)
