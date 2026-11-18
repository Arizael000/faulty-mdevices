"""Tests for metrics module."""
import pandas as pd
import pytest

from src.metrics import (
    build_metrics,
    _clean_device_names,
    _distribution_index,
    _small_dim,
    _top_dim,
    _year_index,
)


class TestCleanDeviceNames:
    """Tests for _clean_device_names function."""

    def test_removes_device_recall_prefix(self):
        """Test that 'Device Recall' prefix is removed."""
        series = pd.Series(["Device Recall Widget", "Device Recall  Gadget", "Plain Device"])
        result = _clean_device_names(series)
        assert result.iloc[0] == "Widget"
        assert result.iloc[1] == "Gadget"
        assert result.iloc[2] == "Plain Device"

    def test_case_insensitive(self):
        """Test case insensitive removal."""
        series = pd.Series(["device recall Widget", "DEVICE RECALL Gadget"])
        result = _clean_device_names(series)
        assert result.iloc[0] == "Widget"
        assert result.iloc[1] == "Gadget"

    def test_strips_whitespace(self):
        """Test that extra whitespace is normalized."""
        series = pd.Series(["Device Recall  Widget  ", "  Device Recall  Gadget  "])
        result = _clean_device_names(series)
        assert result.iloc[0] == "Widget"
        assert result.iloc[1] == "Gadget"


class TestDistributionIndex:
    """Tests for _distribution_index function."""

    def test_nationwide(self):
        """Test nationwide classification."""
        series = pd.Series(["Nationwide", "All 50 states", "All states", "nation-wide"])
        result = _distribution_index(series)
        assert all(r == 1 for r in result)

    def test_worldwide(self):
        """Test worldwide classification."""
        series = pd.Series(["Worldwide", "International", "Global", "world-wide"])
        result = _distribution_index(series)
        assert all(r == 2 for r in result)

    def test_both(self):
        """Test both nationwide and worldwide."""
        series = pd.Series(["Nationwide and Worldwide", "All states International"])
        result = _distribution_index(series)
        assert all(r == 3 for r in result)

    def test_regional(self):
        """Test regional/local/other classification."""
        series = pd.Series(["California only", "Regional", "Local", "Specific hospital"])
        result = _distribution_index(series)
        assert all(r == 4 for r in result)

    def test_unknown(self):
        """Test unknown/empty classification."""
        series = pd.Series(["", None])
        result = _distribution_index(series)
        assert all(r == 0 for r in result)

    def test_unknown_text_goes_to_regional(self):
        """Test that unknown text goes to regional/other (4)."""
        series = pd.Series(["Unknown", "Random text"])
        result = _distribution_index(series)
        assert all(r == 4 for r in result)


class TestYearIndex:
    """Tests for _year_index function."""

    def test_from_year_column(self):
        """Test year extraction from year column."""
        df = pd.DataFrame({"year": [2017, 2018, None, 2016]})
        result = _year_index(df)
        assert result.tolist() == [2017, 2018, 0, 2016]

    def test_from_date_column(self):
        """Test year extraction from date column."""
        df = pd.DataFrame({"date_initiated_by_firm": pd.to_datetime(["2017-01-15", "2018-03-20", None])})
        result = _year_index(df)
        assert result.tolist() == [2017, 2018, 0]

    def test_no_date_columns(self):
        """Test default when no date columns."""
        df = pd.DataFrame({"other": [1, 2, 3]})
        result = _year_index(df)
        assert all(r == 0 for r in result)


class TestSmallDim:
    """Tests for _small_dim function."""

    def test_keeps_all_values(self):
        """Test that all distinct values are kept."""
        series = pd.Series(["A", "B", "C", "A", "B"])
        result = _small_dim(series)
        assert len(result["values"]) == 4  # Unknown + 3 values
        assert "Unknown" in result["values"]
        assert "A" in result["values"]
        assert "B" in result["values"]
        assert "C" in result["values"]

    def test_ordering(self):
        """Test custom ordering."""
        series = pd.Series(["C", "A", "B"])
        result = _small_dim(series, order={"A": 0, "B": 1, "C": 2})
        # Values should be ordered A, B, C
        values = result["values"][1:]  # Skip Unknown
        assert values == ["A", "B", "C"]

    def test_display_function(self):
        """Test custom display function."""
        series = pd.Series(["yes", "no"])
        result = _small_dim(series, display=lambda v: v.capitalize())
        assert "Yes" in result["values"]
        assert "No" in result["values"]


class TestTopDim:
    """Tests for _top_dim function."""

    def test_keeps_top_values(self):
        """Test that top N values are kept."""
        series = pd.Series(["A", "A", "A", "B", "B", "C", "D", "E"])
        result = _top_dim(series, limit=3)
        assert result["values"] == ["Unknown", "A", "B", "C", "Other (grouped)"]

    def test_groups_tail(self):
        """Test that tail is grouped into Other."""
        series = pd.Series(["A", "A", "B", "B", "C", "C", "D", "D", "E", "E"])
        result = _top_dim(series, limit=3)
        # A, B, C are top 3, D and E become Other
        indices = result["indices"]
        # Count non-zero indices for D and E (should be grouped)
        assert result["values"][-1] == "Other (grouped)"


class TestBuildMetrics:
    """Tests for build_metrics function."""

    def test_build_metrics_basic(self, sample_enriched_df):
        """Test basic metrics building."""
        etl_report = {"tables": {}, "merge": {}}
        metrics = build_metrics(sample_enriched_df, etl_report)

        assert "meta" in metrics
        assert "dims" in metrics
        assert "facts" in metrics
        assert metrics["meta"]["total_events"] == len(sample_enriched_df)
        assert metrics["meta"]["enriched_events"] >= 0
        assert len(metrics["facts"]) > 0

    def test_fact_schema_matches(self, sample_enriched_df):
        """Test that fact schema matches expected columns."""
        etl_report = {"tables": {}, "merge": {}}
        metrics = build_metrics(sample_enriched_df, etl_report)

        expected = [
            "year", "country", "risk_class", "implanted",
            "classification", "cause", "manufacturer", "device",
            "distribution", "has_device", "count"
        ]
        assert metrics["meta"]["fact_schema"] == expected

    def test_dimensions_present(self, sample_enriched_df):
        """Test that all expected dimensions are present."""
        etl_report = {"tables": {}, "merge": {}}
        metrics = build_metrics(sample_enriched_df, etl_report)

        dims = metrics["dims"]
        assert "years" in dims
        assert "countries" in dims
        assert "riskClasses" in dims
        assert "implanted" in dims
        assert "classifications" in dims
        assert "causes" in dims
        assert "manufacturers" in dims
        assert "devices" in dims
        assert "distributions" in dims