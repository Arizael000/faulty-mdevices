"""Tests for merge module."""
import pandas as pd
import pytest

from src.merge import build_enriched, load_enriched


class TestBuildEnriched:
    """Tests for build_enriched function."""

    def test_build_enriched_left_join_keeps_all_events(self, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that left join keeps all events."""
        enriched, inner, report = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)

        assert len(enriched) == len(sample_events_df)  # All events kept
        assert report["events_rows"] == len(sample_events_df)
        assert report["matched_rows"] == 3  # 3 events have matching devices
        assert report["unmatched_rows"] == 1  # 1 event has no matching device (device_id=999)

    def test_build_enriched_has_device_flag(self, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that has_device flag is correctly set."""
        enriched, inner, _ = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)

        assert enriched["has_device"].sum() == 3
        assert enriched["has_device"].iloc[3] == 0  # Last event has no device

    def test_build_enriched_inner_join_only_matched(self, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that inner join only has matched rows."""
        enriched, inner, report = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)

        assert len(inner) == report["matched_rows"]
        assert all(inner["has_device"] == 1)

    def test_build_enriched_manufacturer_resolution(self, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that matched devices resolve manufacturers."""
        enriched, inner, report = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)

        assert report["manufacturers_unmatched_inner"] == 0
        # All matched rows should have manufacturer_name
        assert inner["manufacturer_name"].notna().all()

    def test_build_enriched_date_parsing(self, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that date_initiated_by_firm is parsed to datetime."""
        enriched, _, _ = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)

        assert pd.api.types.is_datetime64_any_dtype(enriched["date_initiated_by_firm"])
        assert "year" in enriched.columns
        assert enriched["year"].iloc[0] == 2017

    def test_build_enriched_column_renaming(self, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that columns are properly renamed."""
        enriched, _, _ = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)

        assert "event_id" in enriched.columns
        assert "device_name" in enriched.columns
        assert "manufacturer_name" in enriched.columns
        assert "event_country" in enriched.columns
        assert "device_key" not in enriched.columns
        assert "manufacturer_key" not in enriched.columns


class TestLoadEnriched:
    """Tests for load_enriched function."""

    def test_load_enriched_parses_dates(self, tmp_path, sample_events_df, sample_devices_df, sample_manufacturers_df):
        """Test that load_enriched parses dates correctly."""
        from src.merge import build_enriched

        enriched, _, _ = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)
        csv_path = tmp_path / "test_enriched.csv"
        enriched.to_csv(csv_path, index=False)

        loaded, report = load_enriched(csv_path)

        assert pd.api.types.is_datetime64_any_dtype(loaded["date_initiated_by_firm"])
        assert "year" in loaded.columns
        assert report["loaded_from_csv"] is True
        assert report["events_rows"] == len(enriched)