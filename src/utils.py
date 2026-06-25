import pandas as pd
import numpy as np
from pathlib import Path
from config import RAW_DATA_DIR


def load_csv(filename: str | None = None, **kwargs) -> pd.DataFrame:
    csv_files = list(RAW_DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files in {RAW_DATA_DIR}")
    path = RAW_DATA_DIR / filename if filename else csv_files[0]
    return pd.read_csv(path, encoding="utf-8", low_memory=False, **kwargs)


def split_column_types(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    return num_cols, cat_cols


def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    report = pd.DataFrame({
        "dtype": df.dtypes,
        "non_null": df.notna().sum(),
        "missing": df.isna().sum(),
        "%": (df.isna().sum() / len(df) * 100).round(2),
    })
    return report.sort_values("missing", ascending=False)
