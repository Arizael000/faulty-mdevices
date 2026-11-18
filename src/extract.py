"""Extraction layer: load the raw ICIJ CSV files."""

from __future__ import annotations

import pandas as pd

from .utils import find_raw_csv, file_checksum


def _load(prefix: str) -> tuple[pd.DataFrame, str, str]:
    path = find_raw_csv(prefix)
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    checksum = file_checksum(path)
    return df, path.name, checksum


def load_devices() -> tuple[pd.DataFrame, str, str]:
    return _load("devices")


def load_events() -> tuple[pd.DataFrame, str, str]:
    return _load("events")


def load_manufacturers() -> tuple[pd.DataFrame, str, str]:
    return _load("manufacturers")
