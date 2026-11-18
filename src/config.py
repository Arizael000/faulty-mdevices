"""Project paths and shared constants.

Paths are resolved from this file instead of the current working directory so
the pipeline behaves the same no matter where it is launched from.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Raw CSV prefixes mapped to their filename pattern.
RAW_PATTERNS = {
    "devices": "devices-*.csv",
    "events": "events-*.csv",
    "manufacturers": "manufacturers-*.csv",
}

# Processing rules inherited from the exploratory notebooks.
# These can be overridden at runtime via CLI arguments.
NULL_DROP_THRESHOLD = 0.40  # columns above this null share are dropped
EVENTS_MIN_NON_NULL = 15  # events must keep at least this many values
CATEGORY_CARDINALITY = 0.05  # object columns below this ratio become category
TOP_DIM_VALUES = 15  # values kept before folding the rest into "Other (grouped)"

RANDOM_SEED = 42

PROCESSED_FILES = {
    "devices": PROCESSED_DATA_DIR / "devicesProcessed.csv",
    "events": PROCESSED_DATA_DIR / "eventsProcessed.csv",
    "manufacturers": PROCESSED_DATA_DIR / "manufacturersProcessed.csv",
    "enriched": PROCESSED_DATA_DIR / "eventsEnriched.csv",
    "inner_merge": PROCESSED_DATA_DIR / "mergedDevicesEvents.csv",
    "etl_report": PROCESSED_DATA_DIR / "etl_report.json",
}


# Runtime overrides for thresholds (set by CLI)
_runtime_overrides: dict = {}


def set_runtime_overrides(**kwargs) -> None:
    """Set runtime overrides for configuration values."""
    global _runtime_overrides
    _runtime_overrides.update(kwargs)


def get_null_drop_threshold() -> float:
    return _runtime_overrides.get("null_drop_threshold", NULL_DROP_THRESHOLD)


def get_events_min_non_null() -> int:
    return _runtime_overrides.get("events_min_non_null", EVENTS_MIN_NON_NULL)


def get_category_cardinality() -> float:
    return _runtime_overrides.get("category_cardinality", CATEGORY_CARDINALITY)


def get_top_dim_values() -> int:
    return _runtime_overrides.get("top_dim_values", TOP_DIM_VALUES)


def ensure_directories() -> None:
    """Create the directories the pipeline writes to."""
    for path in (RAW_DATA_DIR, PROCESSED_DATA_DIR, DASHBOARD_DIR, TEMPLATES_DIR):
        path.mkdir(parents=True, exist_ok=True)
