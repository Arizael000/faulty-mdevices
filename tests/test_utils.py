"""Tests for utils module."""
import pandas as pd
import pytest
from pathlib import Path

from src.utils import (
    clean_column_names,
    strip_strings,
    optimize_categories,
    drop_constant_columns,
    drop_duplicate_columns,
    missing_report,
    save_csv,
    to_python_int,
    to_python_float,
)


class TestCleanColumnNames:
    """Tests for clean_column_names function."""

    def test_converts_to_snake_case(self):
        """Test conversion to snake_case."""
        df = pd.DataFrame(columns=["Device Name", "Risk Class", "Manufacturer ID"])
        result, rename_map = clean_column_names(df)
        assert list(result.columns) == ["device_name", "risk_class", "manufacturer_id"]
        assert rename_map == {
            "Device Name": "device_name",
            "Risk Class": "risk_class",
            "Manufacturer ID": "manufacturer_id",
        }

    def test_handles_special_characters(self):
        """Test removal of special characters."""
        df = pd.DataFrame(columns=["Col@Name!", "Col#Name$", "Col%Name^"])
        result, rename_map = clean_column_names(df)
        # All special chars removed, all become "colname" (duplicates not handled by this function)
        assert list(result.columns) == ["colname", "colname", "colname"]
        assert rename_map == {
            "Col@Name!": "colname",
            "Col#Name$": "colname",
            "Col%Name^": "colname",
        }

    def test_already_clean_names_unchanged(self):
        """Test that already snake_case names are unchanged."""
        df = pd.DataFrame(columns=["device_name", "risk_class", "manufacturer_id"])
        result, rename_map = clean_column_names(df)
        assert list(result.columns) == ["device_name", "risk_class", "manufacturer_id"]
        assert rename_map == {}

    def test_hyphens_removed(self):
        """Test that hyphens are removed (not converted to underscores)."""
        df = pd.DataFrame(columns=["Risk-Class", "Device-Name"])
        result, _ = clean_column_names(df)
        assert list(result.columns) == ["riskclass", "devicename"]


class TestStripStrings:
    """Tests for strip_strings function."""

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        df = pd.DataFrame({"col": ["  hello  ", "world  ", "  test"]})
        strip_strings(df)
        assert df["col"].tolist() == ["hello", "world", "test"]

    def test_replaces_nan_string(self):
        """Test that 'nan' string becomes None."""
        df = pd.DataFrame({"col": ["hello", "nan", "world"]})
        strip_strings(df)
        assert df["col"].tolist() == ["hello", None, "world"]

    def test_only_object_columns(self):
        """Test that only object/string columns are processed."""
        df = pd.DataFrame({"text": ["  a  ", "  b  "], "num": [1, 2]})
        strip_strings(df)
        assert df["text"].tolist() == ["a", "b"]
        assert df["num"].tolist() == [1, 2]  # Unchanged


class TestOptimizeCategories:
    """Tests for optimize_categories function."""

    def test_converts_low_cardinality(self):
        """Test conversion of low cardinality columns."""
        df = pd.DataFrame({"cat": ["A", "B", "A", "B", "A"] * 10})  # 2 unique out of 50
        optimize_categories(df)
        assert df["cat"].dtype.name == "category"

    def test_keeps_high_cardinality(self):
        """Test that high cardinality columns stay as object."""
        df = pd.DataFrame({"cat": [f"value_{i}" for i in range(100)]})  # 100 unique out of 100
        optimize_categories(df)
        assert df["cat"].dtype.name == "object"

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        df = pd.DataFrame({"cat": pd.Series(dtype=object)})
        optimize_categories(df)  # Should not error
        assert len(df) == 0


class TestDropConstantColumns:
    """Tests for drop_constant_columns function."""

    def test_drops_constant_column(self):
        """Test dropping column with single value."""
        df = pd.DataFrame({"const": [1, 1, 1], "var": [1, 2, 3]})
        dropped = drop_constant_columns(df)
        assert "const" in dropped
        assert "const" not in df.columns
        assert "var" in df.columns

    def test_drops_all_null_column(self):
        """Test dropping all-null column."""
        df = pd.DataFrame({"const": [None, None, None], "var": [1, 2, 3]})
        dropped = drop_constant_columns(df)
        assert "const" in dropped

    def test_keeps_varying_column(self):
        """Test that varying columns are kept."""
        df = pd.DataFrame({"var": [1, 2, 3]})
        dropped = drop_constant_columns(df)
        assert dropped == []
        assert "var" in df.columns


class TestDropDuplicateColumns:
    """Tests for drop_duplicate_columns function."""

    def test_drops_duplicate_values(self):
        """Test dropping column with identical values to another."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [1, 2, 3], "c": [4, 5, 6]})
        dropped = drop_duplicate_columns(df)
        assert "b" in dropped
        assert "b" not in df.columns
        assert "a" in df.columns
        assert "c" in df.columns

    def test_drops_all_null_duplicates(self):
        """Test dropping duplicate all-null columns."""
        df = pd.DataFrame({"a": [None, None], "b": [None, None]})
        dropped = drop_duplicate_columns(df)
        assert "b" in dropped


class TestMissingReport:
    """Tests for missing_report function."""

    def test_reports_correctly(self):
        """Test missing report output."""
        df = pd.DataFrame({
            "complete": [1, 2, 3],
            "partial": [1, None, 3],
            "empty": [None, None, None],
        })
        report = missing_report(df)
        assert report.loc["complete", "missing"] == 0
        assert report.loc["partial", "missing"] == 1
        assert report.loc["empty", "missing"] == 3
        assert report.loc["empty", "missing_pct"] == 100.0


class TestSaveCSV:
    """Tests for save_csv function."""

    def test_saves_csv(self, tmp_path):
        """Test CSV saving."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        path = tmp_path / "test.csv"
        save_csv(df, path)
        assert path.exists()
        loaded = pd.read_csv(path)
        assert loaded.shape == (2, 2)


class TestToPythonInt:
    """Tests for to_python_int function."""

    def test_converts_numpy_int(self):
        """Test numpy int conversion."""
        import numpy as np
        assert to_python_int(np.int64(42)) == 42
        assert to_python_int(np.int32(42)) == 42

    def test_converts_float(self):
        """Test float conversion."""
        assert to_python_int(42.0) == 42

    def test_handles_nan(self):
        """Test NaN handling."""
        import numpy as np
        assert to_python_int(np.nan) == 0
        assert to_python_int(float('nan')) == 0

    def test_handles_none(self):
        """Test None handling."""
        assert to_python_int(None) == 0


class TestToPythonFloat:
    """Tests for to_python_float function."""

    def test_rounds_correctly(self):
        """Test rounding."""
        assert to_python_float(1.23456) == 1.23
        assert to_python_float(1.235) == 1.24

    def test_handles_nan(self):
        """Test NaN handling."""
        import numpy as np
        assert to_python_float(np.nan) == 0.0

    def test_handles_none(self):
        """Test None handling."""
        assert to_python_float(None) == 0.0

    def test_custom_digits(self):
        """Test custom decimal places."""
        assert to_python_float(1.23456, digits=4) == 1.2346


class TestFileChecksum:
    """Tests for file_checksum function."""

    def test_file_checksum_sha256(self, tmp_path):
        """Test SHA256 checksum computation."""
        from src.utils import file_checksum
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        checksum = file_checksum(test_file, "sha256")
        # Known SHA256 of "hello world"
        assert checksum == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_file_checksum_md5(self, tmp_path):
        """Test MD5 checksum computation."""
        from src.utils import file_checksum
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        checksum = file_checksum(test_file, "md5")
        # Known MD5 of "hello world"
        assert checksum == "5eb63bbbe01eeed093cb22bb8f5acdc3"