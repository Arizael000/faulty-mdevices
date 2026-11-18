"""Tests for pipeline module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import logging

from src.pipeline import run, _print_table_report


class TestPipeline:
    """Tests for pipeline module."""

    def test_print_table_report(self, capsys):
        """Test table report printing."""
        report = {
            "raw_rows": 1000,
            "raw_columns": 10,
            "clean_rows": 800,
            "clean_columns": 8,
            "dropped_rows": 200,
            "dropped_columns": ["a", "b"],
        }
        logger = logging.getLogger("test")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        _print_table_report(logger, "test", report)
        captured = capsys.readouterr()
        # Logger outputs to stderr by default
        assert "test" in captured.err
        assert "1,000" in captured.err
        assert "800" in captured.err
        assert "200" in captured.err

    @patch("src.pipeline.load_devices")
    @patch("src.pipeline.load_events")
    @patch("src.pipeline.load_manufacturers")
    @patch("src.pipeline.transform_devices")
    @patch("src.pipeline.transform_events")
    @patch("src.pipeline.transform_manufacturers")
    @patch("src.pipeline.save_csv")
    @patch("src.pipeline.build_enriched")
    @patch("src.pipeline.build_etl_report")
    @patch("src.pipeline.validate_tables")
    @patch("src.pipeline.build_metrics")
    @patch("src.pipeline.generate_dashboard")
    @patch("src.config.ensure_directories")
    def test_run_full_pipeline(
        self,
        mock_ensure_dirs,
        mock_generate_dashboard,
        mock_build_metrics,
        mock_validate,
        mock_build_etl,
        mock_build_enriched,
        mock_save_csv,
        mock_transform_mfr,
        mock_transform_evt,
        mock_transform_dev,
        mock_load_mfr,
        mock_load_evt,
        mock_load_dev,
    ):
        """Test full pipeline execution."""
        # Setup mocks
        mock_load_dev.return_value = (pd.DataFrame({"id": [1]}), "devices.csv", "abc123")
        mock_load_evt.return_value = (pd.DataFrame({"id": [1]}), "events.csv", "def456")
        mock_load_mfr.return_value = (pd.DataFrame({"id": [1]}), "manufacturers.csv", "ghi789")

        mock_transform_dev.return_value = (pd.DataFrame({"id": [1]}), {"clean_rows": 1, "raw_rows": 1, "raw_columns": 1, "clean_columns": 1, "dropped_rows": 0, "dropped_columns": [], "duplicates_removed": 0, "dates_parsed": 0, "remaining_missing": 0, "notes": []})
        mock_transform_evt.return_value = (pd.DataFrame({"id": [1]}), {"clean_rows": 1, "raw_rows": 1, "raw_columns": 1, "clean_columns": 1, "dropped_rows": 0, "dropped_columns": [], "duplicates_removed": 0, "dates_parsed": 0, "remaining_missing": 0, "notes": []})
        mock_transform_mfr.return_value = (pd.DataFrame({"id": [1]}), {"clean_rows": 1, "raw_rows": 1, "raw_columns": 1, "clean_columns": 1, "dropped_rows": 0, "dropped_columns": [], "duplicates_removed": 0, "dates_parsed": 0, "remaining_missing": 0, "notes": []})

        mock_build_enriched.return_value = (
            pd.DataFrame({"event_id": [1], "has_device": [1]}),
            pd.DataFrame({"event_id": [1]}),
            {"events_rows": 1, "matched_rows": 1, "unmatched_rows": 0, "coverage_pct": 100.0, "inner_rows": 1, "manufacturers_unmatched_inner": 0, "date_min": "2017-01-01", "date_max": "2017-01-01"}
        )

        mock_build_etl.return_value = {"tables": {}, "merge": {}}
        mock_validate.return_value = {"passed": 13, "failed": 0, "total": 13, "checks": []}
        mock_build_metrics.return_value = {
            "meta": {
                "total_events": 1,
                "enriched_events": 1,
                "coverage_pct": 100.0,
                "date_min": "2017-01-01",
                "date_max": "2017-01-01",
                "fact_schema": [],
                "etl": {}
            },
            "dims": {
                "countries": ["Unknown", "USA"],
                "manufacturers": ["Unknown", "Mfg A", "Other (grouped)"],
                "devices": ["Unknown", "Device A", "Other (grouped)"]
            },
            "facts": []
        }
        mock_generate_dashboard.return_value = MagicMock()

        # Run pipeline
        result = run(skip_etl=False)

        # Verify calls
        mock_ensure_dirs.assert_called_once()
        mock_load_dev.assert_called_once()
        mock_load_evt.assert_called_once()
        mock_load_mfr.assert_called_once()
        mock_transform_dev.assert_called_once()
        mock_transform_evt.assert_called_once()
        mock_transform_mfr.assert_called_once()
        mock_build_enriched.assert_called_once()
        mock_build_etl.assert_called_once()
        mock_validate.assert_called_once()
        mock_build_metrics.assert_called_once()
        mock_generate_dashboard.assert_called_once()

        assert result["meta"]["total_events"] == 1

    @patch("src.pipeline.load_enriched")
    @patch("src.pipeline.build_metrics")
    @patch("src.pipeline.generate_dashboard")
    @patch("src.config.ensure_directories")
    @patch("src.config.PROCESSED_FILES")
    def test_run_skip_etl(
        self,
        mock_processed_files,
        mock_ensure_dirs,
        mock_generate_dashboard,
        mock_build_metrics,
        mock_load_enriched,
    ):
        """Test pipeline with --skip-etl flag."""
        mock_load_enriched.return_value = (
            pd.DataFrame({"event_id": [1], "has_device": [1]}),
            {"events_rows": 1, "matched_rows": 1, "unmatched_rows": 0, "coverage_pct": 100.0}
        )
        mock_build_metrics.return_value = {
            "meta": {
                "total_events": 1,
                "enriched_events": 1,
                "coverage_pct": 100.0,
                "date_min": "2017-01-01",
                "date_max": "2017-01-01",
                "fact_schema": [],
                "etl": {}
            },
            "dims": {
                "countries": ["Unknown", "USA"],
                "manufacturers": ["Unknown", "Mfg A", "Other (grouped)"],
                "devices": ["Unknown", "Device A", "Other (grouped)"]
            },
            "facts": []
        }
        mock_generate_dashboard.return_value = MagicMock()
        # Mock processed files to not exist (so validation is skipped)
        mock_enriched = MagicMock()
        mock_enriched.exists.return_value = True
        mock_devices = MagicMock()
        mock_devices.exists.return_value = False
        mock_events = MagicMock()
        mock_events.exists.return_value = False
        mock_manufacturers = MagicMock()
        mock_manufacturers.exists.return_value = False
        mock_etl_report = MagicMock()
        mock_etl_report.exists.return_value = False
        mock_processed_files.__getitem__.side_effect = lambda k: {
            "enriched": mock_enriched,
            "devices": mock_devices,
            "events": mock_events,
            "manufacturers": mock_manufacturers,
            "etl_report": mock_etl_report,
        }[k]

        result = run(skip_etl=True)

        mock_load_enriched.assert_called_once()
        mock_build_metrics.assert_called_once()
        mock_generate_dashboard.assert_called_once()
        # Should NOT call extract/transform/merge
        assert result is not None