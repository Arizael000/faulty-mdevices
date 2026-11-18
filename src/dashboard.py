"""Dashboard generator.

Keeps a single HTML/CSS/JS deliverable: the metrics object is injected into
``dashboard/app.js`` from a template so the page works from the file system.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import DASHBOARD_DIR, TEMPLATES_DIR

DATA_PLACEHOLDER = "/*__DATA__*/"


def generate_dashboard(
    metrics: dict,
    template_path: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    template_path = template_path or TEMPLATES_DIR / "app.js"
    output_path = output_path or DASHBOARD_DIR / "app.js"

    if not template_path.exists():
        raise FileNotFoundError(f"Dashboard template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    if DATA_PLACEHOLDER not in template:
        raise ValueError(f"Template is missing the {DATA_PLACEHOLDER} marker")

    payload = json.dumps(metrics, ensure_ascii=False, separators=(",", ":"))
    rendered = template.replace(DATA_PLACEHOLDER, payload, 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path
