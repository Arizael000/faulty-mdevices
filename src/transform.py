"""Transformation layer.

Applies, in code, the cleaning decisions documented in the exploratory
notebooks. Every function returns the cleaned dataframe plus a small report
that is later embedded in the dashboard's data-quality panel.
"""

from __future__ import annotations

import pandas as pd

from .config import (
    get_events_min_non_null,
    get_null_drop_threshold,
)
from .utils import (
    clean_column_names,
    drop_constant_columns,
    drop_duplicate_columns,
    missing_report,
    optimize_categories,
    strip_strings,
    to_python_int,
)

EVENT_DROP_COLUMNS = [
    "url",  # HTTP 302 redirects, no usable data
    "updated_at",  # identical to created_at
    "target_audience",  # 99.65% null
    "authorities_link",  # link, unused
    "data_notes",  # 53.65% null
    "date_posted",  # 64.64% null
    "date_terminated",  # 74.80% null
    "status",  # 70.77% null
    "date_updated",  # 99.82% null
    "action_level",  # 98.03% null
    "create_date",  # 95.84% null
]

EVENT_EXTRA_DROPS = ["documents", "action_summary", "action_classification"]


def _report(
    dataset: str,
    source_file: str,
    raw_shape: tuple[int, int],
    clean_df: pd.DataFrame,
    *,
    dropped_columns: list[str] | None = None,
    dropped_rows: int = 0,
    duplicates_removed: int = 0,
    dates_parsed: int = 0,
    notes: list[str] | None = None,
) -> dict:
    return {
        "dataset": dataset,
        "source_file": source_file,
        "raw_rows": to_python_int(raw_shape[0]),
        "raw_columns": to_python_int(raw_shape[1]),
        "clean_rows": to_python_int(len(clean_df)),
        "clean_columns": to_python_int(clean_df.shape[1]),
        "dropped_columns": dropped_columns or [],
        "dropped_rows": to_python_int(dropped_rows),
        "duplicates_removed": to_python_int(duplicates_removed),
        "dates_parsed": to_python_int(dates_parsed),
        "remaining_missing": to_python_int(clean_df.isna().sum().sum()),
        "notes": notes or [],
    }


def transform_devices(df: pd.DataFrame, source_file: str = "") -> tuple[pd.DataFrame, dict]:
    """Clean the devices table (section 1 notebooks)."""
    raw_shape = df.shape
    notes = [
        "Rows with any missing value were removed (complete-case analysis).",
        "updated_at was dropped: it matched created_at in 99.31% of rows.",
        "number was dropped: free-form serial/catalog text, not usable as a key.",
        "'Not Classified' was unified into 'Unclassified' in risk_class.",
        "Constant and duplicate columns (country) were dropped.",
    ]

    n_before = len(df)
    df = df.dropna()
    null_rows_removed = n_before - len(df)

    df = df.drop(columns=["updated_at", "number"], errors="ignore")
    df.loc[df["risk_class"] == "Not Classified", "risk_class"] = "Unclassified"

    constant = drop_constant_columns(df)
    duplicates = drop_duplicate_columns(df)
    df, renamed = clean_column_names(df)
    strip_strings(df)
    optimize_categories(df)

    n_before_dedupe = len(df)
    df = df.drop_duplicates()
    duplicates_rows = n_before_dedupe - len(df)

    report = _report(
        "devices",
        source_file,
        raw_shape,
        df,
        dropped_columns=["updated_at", "number", *constant, *duplicates],
        dropped_rows=null_rows_removed + duplicates_rows,
        duplicates_removed=duplicates_rows,
        notes=notes,
    )
    report["rows_with_nulls_removed"] = to_python_int(null_rows_removed)
    report["renamed_columns"] = renamed
    return df.reset_index(drop=True), report


def transform_events(df: pd.DataFrame, source_file: str = "") -> tuple[pd.DataFrame, dict]:
    """Clean the events table (section 2 notebooks)."""
    raw_shape = df.shape
    min_non_null = get_events_min_non_null()
    notes = [
        "11 link/date/text columns were dropped during EDA.",
        f"Rows kept only if they had at least {min_non_null} of the 19 remaining values.",
        "date was dropped: 99.6% null even after the row filter.",
        "documents, action_summary and action_classification were dropped.",
        "date_initiated_by_firm was parsed to datetime; it covers 1997-2018.",
    ]

    n_before = len(df)
    df = df.drop(columns=EVENT_DROP_COLUMNS, errors="ignore")

    n_after_columns = len(df)
    df = df.dropna(thresh=min_non_null)
    rows_removed = n_after_columns - len(df)

    df = df.drop(columns=["date", *EVENT_EXTRA_DROPS], errors="ignore")
    strip_strings(df)

    if "date_initiated_by_firm" in df.columns:
        df["date_initiated_by_firm"] = pd.to_datetime(
            df["date_initiated_by_firm"], errors="coerce", format="ISO8601"
        )
    dates_parsed = to_python_int(df["date_initiated_by_firm"].notna().sum())

    optimize_categories(df)

    n_before_dedupe = len(df)
    df = df.drop_duplicates()
    duplicates_rows = n_before_dedupe - len(df)

    report = _report(
        "events",
        source_file,
        raw_shape,
        df,
        dropped_columns=[*EVENT_DROP_COLUMNS, "date", *EVENT_EXTRA_DROPS],
        dropped_rows=(n_before - len(df)),
        duplicates_removed=duplicates_rows,
        dates_parsed=dates_parsed,
        notes=notes,
    )
    report["rows_removed_by_threshold"] = to_python_int(rows_removed)
    return df.reset_index(drop=True), report


def transform_manufacturers(
    df: pd.DataFrame, source_file: str = ""
) -> tuple[pd.DataFrame, dict]:
    """Clean the manufacturers dimension (section 3 notebooks)."""
    raw_shape = df.shape
    threshold = get_null_drop_threshold()
    notes = [
        f"Columns with more than {threshold*100:.0f}% nulls were dropped (address, comment, representative).",
        "updated_at was dropped: identical to created_at in 100% of rows.",
        "Rows without name were removed (37 rows).",
    ]

    n_before = len(df)
    null_pct = df.isna().mean()
    high_null = null_pct[null_pct > threshold].index.tolist()
    df = df.drop(columns=high_null)
    df = df.drop(columns=["updated_at"], errors="ignore")

    n_with_name = len(df)
    df = df.dropna(subset=["name"])
    missing_names = n_with_name - len(df)

    strip_strings(df)
    optimize_categories(df)

    n_before_dedupe = len(df)
    df = df.drop_duplicates()
    duplicates_rows = n_before_dedupe - len(df)

    report = _report(
        "manufacturers",
        source_file,
        raw_shape,
        df,
        dropped_columns=[*high_null, "updated_at"],
        dropped_rows=missing_names + duplicates_rows,
        duplicates_removed=duplicates_rows,
        notes=notes,
    )
    report["rows_removed_without_name"] = to_python_int(missing_names)
    return df.reset_index(drop=True), report


def build_etl_report(reports: dict[str, dict], merge_report: dict) -> dict:
    """Aggregate per-table reports and the merge diagnostics."""
    from .utils import to_python_float

    report = {"tables": reports, "merge": merge_report}
    report["raw_rows"] = {
        key: value["raw_rows"] for key, value in reports.items()
    }
    report["clean_rows"] = {
        key: value["clean_rows"] for key, value in reports.items()
    }
    report["coverage_pct"] = to_python_float(merge_report.get("coverage_pct", 0.0))
    return report


def drop_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience wrapper kept for exploratory use."""
    return df.dropna()


def nulls_by_column(df: pd.DataFrame) -> pd.DataFrame:
    """Public helper reused by notebooks and tests."""
    return missing_report(df)
