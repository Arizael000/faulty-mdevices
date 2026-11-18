"""End-to-end pipeline CLI.

Usage:
    python -m src.pipeline            # extract -> transform -> merge -> dashboard
    python -m src.pipeline --skip-etl # rebuild the dashboard from processed CSVs
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import pandas as pd

from . import config
from .dashboard import generate_dashboard
from .extract import load_devices, load_events, load_manufacturers
from .merge import build_enriched, load_enriched
from .metrics import build_metrics, summarize
from .transform import (
    build_etl_report,
    transform_devices,
    transform_events,
    transform_manufacturers,
)
from .utils import save_csv
from .validate import validate_tables


def _setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("pipeline")
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def _print_table_report(logger: logging.Logger, name: str, report: dict) -> None:
    logger.info(
        f"  {name:<14} {report['raw_rows']:>9,} x {report['raw_columns']:<3} -> "
        f"{report['clean_rows']:>8,} x {report['clean_columns']:<3}"
        f"  (dropped rows: {report['dropped_rows']:,},"
        f" columns: {len(report['dropped_columns'])})"
    )


def run(skip_etl: bool = False, verbose: bool = False) -> dict:
    logger = _setup_logging(verbose)
    config.ensure_directories()

    if skip_etl:
        enriched_path = config.PROCESSED_FILES["enriched"]
        if not enriched_path.exists():
            raise FileNotFoundError(
                f"{enriched_path} does not exist. Run without --skip-etl first."
            )
        logger.info(f"Loading processed data: {enriched_path.name}")
        enriched, merge_report = load_enriched(enriched_path)
        report_path = config.PROCESSED_FILES["etl_report"]
        if report_path.exists():
            etl_report = json.loads(report_path.read_text(encoding="utf-8"))
        else:
            etl_report = {"merge": merge_report}

        # Try to re-run validation by loading processed tables
        validation = None
        devices_path = config.PROCESSED_FILES["devices"]
        events_path = config.PROCESSED_FILES["events"]
        manufacturers_path = config.PROCESSED_FILES["manufacturers"]
        if all(p.exists() for p in (devices_path, events_path, manufacturers_path)):
            logger.info("Re-running validation on loaded data...")
            devices = pd.read_csv(devices_path, encoding="utf-8", low_memory=False)
            events = pd.read_csv(events_path, encoding="utf-8", low_memory=False)
            manufacturers = pd.read_csv(manufacturers_path, encoding="utf-8", low_memory=False)

            # Parse dates in events
            if "date_initiated_by_firm" in events.columns:
                events["date_initiated_by_firm"] = pd.to_datetime(
                    events["date_initiated_by_firm"], errors="coerce", format="ISO8601"
                )

            reports = etl_report.get("tables", {})
            validation = validate_tables(
                devices, events, manufacturers, enriched, reports, merge_report
            )
            etl_report["validation"] = validation
            logger.info(
                f"  validation: {validation['passed']}/{validation['total']} checks passed"
            )
        else:
            validation = etl_report.get("validation")
            if validation:
                logger.info(
                    f"  validation (from report): "
                    f"{validation['passed']}/{validation['total']} checks passed"
                )
    else:
        logger.info("Extracting raw CSVs...")
        devices_raw, devices_file, devices_checksum = load_devices()
        events_raw, events_file, events_checksum = load_events()
        manufacturers_raw, manufacturers_file, manufacturers_checksum = load_manufacturers()

        logger.info("Transforming tables...")
        devices, devices_report = transform_devices(devices_raw, devices_file)
        events, events_report = transform_events(events_raw, events_file)
        manufacturers, manufacturers_report = transform_manufacturers(
            manufacturers_raw, manufacturers_file
        )

        # Add checksums to reports
        devices_report["source_checksum"] = devices_checksum
        events_report["source_checksum"] = events_checksum
        manufacturers_report["source_checksum"] = manufacturers_checksum

        for name, report in (
            ("devices", devices_report),
            ("events", events_report),
            ("manufacturers", manufacturers_report),
        ):
            _print_table_report(logger, name, report)

        save_csv(devices, config.PROCESSED_FILES["devices"])
        save_csv(events, config.PROCESSED_FILES["events"])
        save_csv(manufacturers, config.PROCESSED_FILES["manufacturers"])

        logger.info("Merging events -> devices -> manufacturers...")
        enriched, inner, merge_report = build_enriched(events, devices, manufacturers)
        save_csv(enriched, config.PROCESSED_FILES["enriched"])
        save_csv(inner, config.PROCESSED_FILES["inner_merge"])

        logger.info(
            f"  device-linked recalls: {merge_report['matched_rows']:,} / "
            f"{merge_report['events_rows']:,} ({merge_report['coverage_pct']}%)"
        )

        etl_report = build_etl_report(
            {
                "devices": devices_report,
                "events": events_report,
                "manufacturers": manufacturers_report,
            },
            merge_report,
        )
        validation = validate_tables(
            devices,
            events,
            manufacturers,
            enriched,
            {
                "devices": devices_report,
                "events": events_report,
                "manufacturers": manufacturers_report,
            },
            merge_report,
        )
        etl_report["validation"] = validation
        config.PROCESSED_FILES["etl_report"].write_text(
            json.dumps(etl_report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(
            f"  validation: {validation['passed']}/{validation['total']} checks passed"
        )

    logger.info("Building dashboard metrics...")
    metrics = build_metrics(enriched, etl_report)

    logger.info("Rendering dashboard/app.js...")
    output = generate_dashboard(metrics)

    logger.info("")
    logger.info("Pipeline complete")
    logger.info("-" * 52)
    logger.info(summarize(metrics))
    logger.info(f"Dashboard data:  {output}")
    logger.info(f"Open:            {config.DASHBOARD_DIR / 'index.html'}")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Faulty Medical Devices ETL pipeline and build the dashboard."
    )
    parser.add_argument(
        "--skip-etl",
        action="store_true",
        help="Reuse data/processed/eventsEnriched.csv instead of re-reading the raw CSVs.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )
    parser.add_argument(
        "--null-drop-threshold",
        type=float,
        default=None,
        help="Drop columns with null percentage above this threshold (default: 0.40).",
    )
    parser.add_argument(
        "--events-min-non-null",
        type=int,
        default=None,
        help="Minimum non-null values required per event row (default: 15).",
    )
    parser.add_argument(
        "--category-cardinality",
        type=float,
        default=None,
        help="Cardinality threshold for category conversion (default: 0.05).",
    )
    parser.add_argument(
        "--top-dim-values",
        type=int,
        default=None,
        help="Number of top values to keep before grouping tail (default: 15).",
    )
    args = parser.parse_args()

    # Apply runtime overrides
    overrides = {}
    if args.null_drop_threshold is not None:
        overrides["null_drop_threshold"] = args.null_drop_threshold
    if args.events_min_non_null is not None:
        overrides["events_min_non_null"] = args.events_min_non_null
    if args.category_cardinality is not None:
        overrides["category_cardinality"] = args.category_cardinality
    if args.top_dim_values is not None:
        overrides["top_dim_values"] = args.top_dim_values
    config.set_runtime_overrides(**overrides)

    started = time.perf_counter()
    try:
        run(skip_etl=args.skip_etl, verbose=args.verbose)
    except Exception as exc:  # noqa: BLE001 - surface a friendly CLI error
        logging.getLogger("pipeline").error(f"Pipeline failed: {exc}")
        raise
    logging.getLogger("pipeline").info(f"Elapsed: {time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
