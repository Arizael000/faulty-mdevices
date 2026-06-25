from pathlib import Path

PROJECT_DIR = Path.cwd()
DATA_DIR = PROJECT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
NOTEBOOKS_DIR = PROJECT_DIR / "notebooks"
FIGURES_DIR = NOTEBOOKS_DIR / "figures"

RANDOM_SEED = 42

for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, FIGURES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
