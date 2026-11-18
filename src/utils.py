"""Shared dataframe helpers used by the ETL steps."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import get_category_cardinality, RAW_DATA_DIR, RAW_PATTERNS


def find_raw_csv(prefix: str) -> Path:
    """Return the newest raw CSV that matches a known dataset prefix."""
    pattern = RAW_PATTERNS.get(prefix)
    if pattern is None:
        raise ValueError(f"Unknown dataset prefix: {prefix!r}")

    matches = sorted(RAW_DATA_DIR.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No raw CSV matching {pattern!r} was found in {RAW_DATA_DIR}"
        )
    return matches[-1]


def clean_column_names(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Normalise column names to snake_case and report the changes."""

    def _clean(name: str) -> str:
        name = name.strip().lower()
        name = re.sub(r"[^\w\s]", "", name)
        name = re.sub(r"[\s\-]+", "_", name)
        return re.sub(r"_+", "_", name).strip("_")

    rename_map = {c: _clean(c) for c in df.columns if _clean(c) != c}
    if rename_map:
        df = df.rename(columns=rename_map)
    return df, rename_map


def strip_strings(df: pd.DataFrame) -> list[str]:
    """Trim whitespace and turn the literal string ``nan`` into a null."""
    columns = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in columns:
        df[col] = df[col].astype(str).str.strip().replace("nan", None)
    return columns


def optimize_categories(
    df: pd.DataFrame, threshold: float | None = None
) -> list[str]:
    """Cast low-cardinality text columns to ``category`` to save memory."""
    if threshold is None:
        threshold = get_category_cardinality()
    converted: list[str] = []
    if len(df) == 0:
        return converted
    for col in df.select_dtypes(include=["object", "string"]).columns:
        if df[col].nunique(dropna=True) / len(df) < threshold:
            df[col] = df[col].astype("category")
            converted.append(col)
    return converted


def drop_constant_columns(df: pd.DataFrame) -> list[str]:
    """Drop columns that hold a single value (including all-null columns)."""
    constant = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    if constant:
        df.drop(columns=constant, inplace=True)
    return constant


def drop_duplicate_columns(df: pd.DataFrame) -> list[str]:
    """Drop columns whose values are identical to an earlier column."""
    duplicates: list[str] = []
    seen: dict[tuple, str] = {}
    for col in df.columns:
        key = tuple(df[col].astype(str).fillna("__NULL__"))
        if key in seen:
            duplicates.append(col)
        else:
            seen[key] = col
    if duplicates:
        df.drop(columns=duplicates, inplace=True)
    return duplicates


def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column null diagnostics."""
    report = pd.DataFrame(
        {
            "dtype": df.dtypes.astype(str),
            "non_null": df.notna().sum(),
            "missing": df.isna().sum(),
            "missing_pct": (df.isna().mean() * 100).round(2),
        }
    )
    return report.sort_values("missing", ascending=False)


def save_csv(df: pd.DataFrame, path: Path) -> Path:
    """Write a dataframe as UTF-8 CSV, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def to_python_int(value) -> int:
    """Convert numpy integers (and NaN) to plain ints for JSON output."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0
    return int(value)


def to_python_float(value, digits: int = 2) -> float:
    """Round a numeric value and convert numpy scalars to plain floats."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0.0
    return round(float(value), digits)


def file_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Compute file checksum."""
    hash_func = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()
