"""Tests for validation module."""
import pandas as pd
import pytest

from src.validate import validate_tables, ALLOWED_RISK, ALLOWED_IMPLANTED
from src.merge import build_enriched


class TestValidateTables:
    """Tests for validate_tables function."""

    def test_validate_tables_all_pass(self, sample_devices_df, sample_events_df, sample_manufacturers_df):
        """Test validation with clean data."""
        from src.transform import transform_devices, transform_events, transform_manufacturers
        from src.merge import build_enriched

        # Transform the data first (as the pipeline does)
        devices_clean, dev_report = transform_devices(sample_devices_df, "test.csv")
        events_clean, evt_report = transform_events(sample_events_df, "test.csv")
        manufacturers_clean, mfr_report = transform_manufacturers(sample_manufacturers_df, "test.csv")

        enriched, _, merge_report = build_enriched(events_clean, devices_clean, manufacturers_clean)

        reports = {
            "devices": dev_report,
            "events": evt_report,
            "manufacturers": mfr_report,
        }

        validation = validate_tables(
            devices_clean, events_clean, manufacturers_clean,
            enriched, reports, merge_report
        )

        assert validation["failed"] == 0
        assert validation["passed"] == validation["total"]
        assert all(check["ok"] for check in validation["checks"])

    def test_validate_devices_id_unique(self, sample_events_df, sample_manufacturers_df):
        """Test that duplicate device IDs are caught."""
        devices = pd.DataFrame({
            "id": [1, 1, 2],  # Duplicate ID
            "manufacturer_id": [10, 10, 20],
            "name": ["A", "B", "C"],
            "risk_class": ["1", "2", "3"],
            "implanted": ["YES", "NO", "YES"],
            "classification": ["Cat A", "Cat B", "Cat C"],
            "code": ["C1", "C2", "C3"],
            "distributed_to": ["Nationwide"] * 3,
            "quantity_in_commerce": [100, 200, 300],
            "number": ["SN1", "SN2", "SN3"],
            "updated_at": ["2020-01-01"] * 3,
            "created_at": ["2020-01-01"] * 3,
            "country": ["USA"] * 3,
            "slug": ["a", "b", "c"],
        })
        enriched, _, merge_report = build_enriched(sample_events_df, devices, sample_manufacturers_df)

        reports = {
            "devices": {"clean_rows": len(devices)},
            "events": {"clean_rows": len(sample_events_df)},
            "manufacturers": {"clean_rows": len(sample_manufacturers_df)},
        }

        validation = validate_tables(devices, sample_events_df, sample_manufacturers_df, enriched, reports, merge_report)

        # Find the check for device ID uniqueness
        device_id_check = next(c for c in validation["checks"] if c["name"] == "devices.id is unique")
        assert device_id_check["ok"] is False
        assert "duplicated ids" in device_id_check["detail"].lower()

    def test_validate_devices_table_complete(self, sample_events_df, sample_manufacturers_df):
        """Test that missing values in devices are caught."""
        devices = pd.DataFrame({
            "id": [1, 2],
            "manufacturer_id": [10, 20],
            "name": ["A", None],  # Missing name
            "risk_class": ["1", "2"],
            "implanted": ["YES", "NO"],
            "classification": ["Cat A", "Cat B"],
            "code": ["C1", "C2"],
            "distributed_to": ["Nationwide", "Worldwide"],
            "quantity_in_commerce": [100, 200],
            "number": ["SN1", "SN2"],
            "updated_at": ["2020-01-01"] * 2,
            "created_at": ["2020-01-01"] * 2,
            "country": ["USA"] * 2,
            "slug": ["a", "b"],
        })
        enriched, _, merge_report = build_enriched(sample_events_df, devices, sample_manufacturers_df)

        reports = {
            "devices": {"clean_rows": len(devices)},
            "events": {"clean_rows": len(sample_events_df)},
            "manufacturers": {"clean_rows": len(sample_manufacturers_df)},
        }

        validation = validate_tables(devices, sample_events_df, sample_manufacturers_df, enriched, reports, merge_report)

        completeness_check = next(c for c in validation["checks"] if c["name"] == "devices table is complete")
        assert completeness_check["ok"] is False

    def test_validate_risk_class_allowed_values(self, sample_events_df, sample_manufacturers_df):
        """Test that invalid risk class values are caught."""
        devices = pd.DataFrame({
            "id": [1, 2],
            "manufacturer_id": [10, 20],
            "name": ["A", "B"],
            "risk_class": ["1", "InvalidClass"],  # Invalid value
            "implanted": ["YES", "NO"],
            "classification": ["Cat A", "Cat B"],
            "code": ["C1", "C2"],
            "distributed_to": ["Nationwide", "Worldwide"],
            "quantity_in_commerce": [100, 200],
            "number": ["SN1", "SN2"],
            "updated_at": ["2020-01-01"] * 2,
            "created_at": ["2020-01-01"] * 2,
            "country": ["USA"] * 2,
            "slug": ["a", "b"],
        })
        enriched, _, merge_report = build_enriched(sample_events_df, devices, sample_manufacturers_df)

        reports = {
            "devices": {"clean_rows": len(devices)},
            "events": {"clean_rows": len(sample_events_df)},
            "manufacturers": {"clean_rows": len(sample_manufacturers_df)},
        }

        validation = validate_tables(devices, sample_events_df, sample_manufacturers_df, enriched, reports, merge_report)

        risk_check = next(c for c in validation["checks"] if c["name"] == "risk_class uses allowed values")
        assert risk_check["ok"] is False
        assert "InvalidClass" in risk_check["detail"]

    def test_validate_implanted_allowed_values(self, sample_events_df, sample_manufacturers_df):
        """Test that invalid implanted values are caught."""
        devices = pd.DataFrame({
            "id": [1, 2],
            "manufacturer_id": [10, 20],
            "name": ["A", "B"],
            "risk_class": ["1", "2"],
            "implanted": ["YES", "Maybe"],  # Invalid value
            "classification": ["Cat A", "Cat B"],
            "code": ["C1", "C2"],
            "distributed_to": ["Nationwide", "Worldwide"],
            "quantity_in_commerce": [100, 200],
            "number": ["SN1", "SN2"],
            "updated_at": ["2020-01-01"] * 2,
            "created_at": ["2020-01-01"] * 2,
            "country": ["USA"] * 2,
            "slug": ["a", "b"],
        })
        enriched, _, merge_report = build_enriched(sample_events_df, devices, sample_manufacturers_df)

        reports = {
            "devices": {"clean_rows": len(devices)},
            "events": {"clean_rows": len(sample_events_df)},
            "manufacturers": {"clean_rows": len(sample_manufacturers_df)},
        }

        validation = validate_tables(devices, sample_events_df, sample_manufacturers_df, enriched, reports, merge_report)

        implanted_check = next(c for c in validation["checks"] if c["name"] == "implanted uses YES/NO")
        assert implanted_check["ok"] is False
        assert "Maybe" in implanted_check["detail"]

    def test_validate_device_join_coverage(self, sample_devices_df, sample_manufacturers_df):
        """Test that low join coverage is caught."""
        # Events with device_ids that don't exist in devices
        events = pd.DataFrame({
            "id": [100, 101, 102, 103, 104],
            "device_id": [999, 998, 997, 996, 995],  # None match
            "country": ["USA"] * 5,
            "date_initiated_by_firm": ["2017-01-15"] * 5,
            "classification": ["Class I"] * 5,
            "determined_cause": ["Cause A"] * 5,
            "distributed_to": ["Nationwide"] * 5,
            "action_summary": [None] * 5,
            "action_classification": [None] * 5,
            "documents": [None] * 5,
            "date": [None] * 5,
            "url": ["http://a"] * 5,
            "updated_at": ["2020-01-01"] * 5,
            "target_audience": [None] * 5,
            "authorities_link": [None] * 5,
            "data_notes": [None] * 5,
            "date_posted": [None] * 5,
            "date_terminated": [None] * 5,
            "status": [None] * 5,
            "date_updated": [None] * 5,
            "action_level": [None] * 5,
            "create_date": [None] * 5,
            "source": ["FDA"] * 5,
            "slug": ["event-1", "event-2", "event-3", "event-4", "event-5"],
            "created_at": ["2020-01-01"] * 5,
        })
        enriched, _, merge_report = build_enriched(events, sample_devices_df, sample_manufacturers_df)

        reports = {
            "devices": {"clean_rows": len(sample_devices_df)},
            "events": {"clean_rows": len(events)},
            "manufacturers": {"clean_rows": len(sample_manufacturers_df)},
        }

        validation = validate_tables(sample_devices_df, events, sample_manufacturers_df, enriched, reports, merge_report)

        coverage_check = next(c for c in validation["checks"] if c["name"] == "device join coverage >= 75%")
        assert coverage_check["ok"] is False
        assert "0%" in coverage_check["detail"] or "0.0%" in coverage_check["detail"]

    def test_validate_event_country_populated(self, sample_devices_df, sample_manufacturers_df):
        """Test that missing event countries are caught."""
        events = pd.DataFrame({
            "id": [100, 101],
            "device_id": [1, 2],
            "country": ["USA", None],  # Missing country
            "date_initiated_by_firm": ["2017-01-15", "2018-03-20"],
            "classification": ["Class I", "Class II"],
            "determined_cause": ["Cause A", "Cause B"],
            "distributed_to": ["Nationwide", "Worldwide"],
            "action_summary": [None, None],
            "action_classification": [None, None],
            "documents": [None, None],
            "date": [None, None],
            "url": ["http://a", "http://b"],
            "updated_at": ["2020-01-01"] * 2,
            "target_audience": [None, None],
            "authorities_link": [None, None],
            "data_notes": [None, None],
            "date_posted": [None, None],
            "date_terminated": [None, None],
            "status": [None, None],
            "date_updated": [None, None],
            "action_level": [None, None],
            "create_date": [None, None],
            "source": ["FDA", "FDA"],
            "slug": ["event-1", "event-2"],
            "created_at": ["2020-01-01"] * 2,
        })
        enriched, _, merge_report = build_enriched(events, sample_devices_df, sample_manufacturers_df)

        reports = {
            "devices": {"clean_rows": len(sample_devices_df)},
            "events": {"clean_rows": len(events)},
            "manufacturers": {"clean_rows": len(sample_manufacturers_df)},
        }

        validation = validate_tables(sample_devices_df, events, sample_manufacturers_df, enriched, reports, merge_report)

        country_check = next(c for c in validation["checks"] if c["name"] == "event_country is populated")
        assert country_check["ok"] is False
        assert "1 recalls without a country" in country_check["detail"]