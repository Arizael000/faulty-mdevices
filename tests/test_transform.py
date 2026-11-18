"""Tests for transform module."""
import pandas as pd
import pytest

from src.transform import (
    transform_devices,
    transform_events,
    transform_manufacturers,
)


class TestTransformDevices:
    """Tests for transform_devices function."""

    def test_transform_devices_basic(self, sample_devices_df):
        """Test basic device transformation."""
        df, report = transform_devices(sample_devices_df, "test.csv")

        assert len(df) == 4  # No rows dropped - all complete
        assert "updated_at" not in df.columns
        assert "number" not in df.columns
        assert "country" not in df.columns
        assert df["risk_class"].iloc[3] == "Unclassified"
        assert report["clean_rows"] == 4
        assert report["rows_with_nulls_removed"] == 0

    def test_transform_devices_drops_null_rows(self):
        """Test that rows with any null are dropped."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "manufacturer_id": [10, 20, 30],
            "name": ["A", "B", None],  # Null in name
            "risk_class": ["1", "2", "3"],
            "implanted": ["YES", "NO", "YES"],
            "classification": ["Cat A", "Cat B", "Cat C"],
            "code": ["C1", "C2", "C3"],
            "distributed_to": ["Nationwide", "Worldwide", "Both"],
            "quantity_in_commerce": [100, 200, 300],
            "number": ["SN1", "SN2", "SN3"],
            "updated_at": ["2020-01-01"] * 3,
            "created_at": ["2020-01-01"] * 3,
            "country": ["USA"] * 3,
            "slug": ["a", "b", "c"],
        })
        result, report = transform_devices(df, "test.csv")
        assert len(result) == 2
        assert report["rows_with_nulls_removed"] == 1

    def test_transform_devices_unifies_not_classified(self):
        """Test that 'Not Classified' becomes 'Unclassified'."""
        df = pd.DataFrame({
            "id": [1, 2],
            "manufacturer_id": [10, 20],
            "name": ["A", "B"],
            "risk_class": ["Not Classified", "2"],
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
        result, _ = transform_devices(df, "test.csv")
        assert result["risk_class"].iloc[0] == "Unclassified"

    def test_transform_devices_removes_duplicates(self):
        """Test that duplicate rows are removed."""
        df = pd.DataFrame({
            "id": [1, 1, 2],
            "manufacturer_id": [10, 10, 20],
            "name": ["A", "A", "B"],
            "risk_class": ["1", "1", "2"],
            "implanted": ["YES", "YES", "NO"],
            "classification": ["Cat A", "Cat A", "Cat B"],
            "code": ["C1", "C1", "C2"],
            "distributed_to": ["Nationwide", "Nationwide", "Worldwide"],
            "quantity_in_commerce": [100, 100, 200],
            "number": ["SN1", "SN1", "SN2"],
            "updated_at": ["2020-01-01"] * 3,
            "created_at": ["2020-01-01"] * 3,
            "country": ["USA"] * 3,
            "slug": ["a", "a", "b"],
        })
        result, report = transform_devices(df, "test.csv")
        assert len(result) == 2
        assert report["duplicates_removed"] == 1


class TestTransformEvents:
    """Tests for transform_events function."""

    def test_transform_events_basic(self, sample_events_df):
        """Test basic event transformation."""
        df, report = transform_events(sample_events_df, "test.csv")

        # Should drop columns with >95% null and extra drops
        assert "url" not in df.columns
        assert "updated_at" not in df.columns
        assert "target_audience" not in df.columns
        assert "documents" not in df.columns
        assert "action_summary" not in df.columns
        assert "action_classification" not in df.columns
        assert "date" not in df.columns
        assert "date_initiated_by_firm" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["date_initiated_by_firm"])
        assert report["clean_rows"] == 4
        assert report["dates_parsed"] == 4

    def test_transform_events_drops_low_data_rows(self):
        """Test that rows with <15 non-null values are dropped."""
        # Create a row with many nulls - need at least 15 non-null after first 11 columns dropped
        df = pd.DataFrame({
            "id": [1, 2],
            "device_id": [10, 20],
            "country": ["USA", "USA"],
            "date_initiated_by_firm": ["2017-01-15", "2018-03-20"],
            "classification": ["Class I", "Class II"],
            "determined_cause": ["Cause A", "Cause B"],
            "distributed_to": ["Nationwide", "Worldwide"],
            "action_summary": ["Summary 1", None],
            "action_classification": ["Type 1", None],
            "documents": ["doc1", None],
            "date": ["2017-01-01", None],
            "url": ["http://a", "http://b"],
            "updated_at": ["2020-01-01", "2020-01-01"],
            "target_audience": ["Public", None],
            "authorities_link": ["link1", None],
            "data_notes": ["note1", None],
            "date_posted": ["2017-01-01", None],
            "date_terminated": ["2017-12-31", None],
            "status": ["Active", None],
            "date_updated": ["2020-01-01", None],
            "action_level": ["Level 1", None],
            "create_date": ["2020-01-01", None],
            "source": ["FDA", "FDA"],
            "slug": ["event-1", "event-2"],
            "created_at": ["2020-01-01", "2020-01-01"],
            "number": ["EVT001", "EVT002"],
        })
        result, report = transform_events(df, "test.csv")
        # Second row has only ~5 non-null values after column drops
        assert len(result) == 1
        assert report["rows_removed_by_threshold"] == 1


class TestTransformManufacturers:
    """Tests for transform_manufacturers function."""

    def test_transform_manufacturers_basic(self, sample_manufacturers_df):
        """Test basic manufacturer transformation."""
        df, report = transform_manufacturers(sample_manufacturers_df, "test.csv")

        assert "address" not in df.columns
        assert "comment" not in df.columns
        assert "representative" not in df.columns
        assert "updated_at" not in df.columns
        assert len(df) == 10  # fixture has 10 rows
        assert report["clean_rows"] == 10

    def test_transform_manufacturers_drops_missing_name(self):
        """Test that rows without name are dropped."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["A", None, "C"],
            "address": ["Addr 1", "Addr 2", "Addr 3"],
            "comment": [None, None, None],
            "representative": [None, None, None],
            "updated_at": ["2020-01-01"] * 3,
            "created_at": ["2020-01-01"] * 3,
            "source": ["FDA"] * 3,
            "slug": ["a", "b", "c"],
        })
        result, report = transform_manufacturers(df, "test.csv")
        assert len(result) == 2
        assert report["rows_removed_without_name"] == 1

    def test_transform_manufacturers_drops_high_null_columns(self):
        """Test that columns with >40% nulls are dropped."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["A", "B", "C", "D", "E"],
            "address": ["Addr 1", None, None, None, None],  # 80% null
            "comment": [None, None, None, None, None],  # 100% null
            "representative": [None, None, "Rep", None, None],  # 80% null
            "updated_at": ["2020-01-01"] * 5,
            "created_at": ["2020-01-01"] * 5,
            "source": ["FDA"] * 5,
            "slug": ["a", "b", "c", "d", "e"],
        })
        result, report = transform_manufacturers(df, "test.csv")
        assert "address" not in result.columns
        assert "comment" not in result.columns
        assert "representative" not in result.columns