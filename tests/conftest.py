"""Pytest configuration and fixtures."""
import pandas as pd
import pytest


@pytest.fixture
def sample_devices_df():
    """Sample devices dataframe for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4],
        "manufacturer_id": [10, 20, 30, 40],
        "name": ["Device A", "Device B", "Device C", "Device D"],
        "risk_class": ["1", "2", "3", "Not Classified"],
        "implanted": ["YES", "NO", "YES", "NO"],
        "classification": ["Cat A", "Cat B", "Cat C", "Cat D"],
        "code": ["C1", "C2", "C3", "C4"],
        "distributed_to": ["Nationwide", "Worldwide", "Both", "Regional"],
        "quantity_in_commerce": [100, 200, 300, 400],
        "number": ["SN001", "SN002", "SN003", "SN004"],
        "updated_at": ["2020-01-01", "2020-01-01", "2020-01-01", "2020-01-01"],
        "created_at": ["2020-01-01", "2020-01-01", "2020-01-01", "2020-01-01"],
        "country": ["USA", "USA", "USA", "USA"],
        "slug": ["device-a", "device-b", "device-c", "device-d"],
    })


@pytest.fixture
def sample_events_df():
    """Sample events dataframe for testing."""
    return pd.DataFrame({
        "id": [100, 101, 102, 103],
        "device_id": [1, 2, 3, 999],
        "country": ["USA", "USA", "AUS", "GBR"],
        "date_initiated_by_firm": ["2017-01-15", "2018-03-20", "2016-07-10", "2015-11-05"],
        "classification": ["Class I", "Class II", "Class III", "Class I"],
        "determined_cause": ["Cause A", "Cause B", "Cause C", "Cause D"],
        "distributed_to": ["Nationwide", "Worldwide", "Both", "Regional"],
        "action_summary": ["Summary 1", "Summary 2", "Summary 3", "Summary 4"],
        "action_classification": ["Type 1", "Type 2", "Type 3", "Type 4"],
        "documents": ["doc1", "doc2", "doc3", "doc4"],
        "date": ["2017-01-01", "2018-01-01", "2016-01-01", "2015-01-01"],
        "url": ["http://a", "http://b", "http://c", "http://d"],
        "updated_at": ["2020-01-01"] * 4,
        "target_audience": ["Public"] * 4,
        "authorities_link": ["link1", "link2", "link3", "link4"],
        "data_notes": ["note1", "note2", "note3", "note4"],
        "date_posted": ["2017-01-01"] * 4,
        "date_terminated": ["2017-12-31"] * 4,
        "status": ["Active"] * 4,
        "date_updated": ["2020-01-01"] * 4,
        "action_level": ["Level 1"] * 4,
        "create_date": ["2020-01-01"] * 4,
        "source": ["FDA", "FDA", "TGA", "MHRA"],
        "slug": ["event-1", "event-2", "event-3", "event-4"],
        "created_at": ["2020-01-01"] * 4,
        "number": ["EVT001", "EVT002", "EVT003", "EVT004"],
    })


@pytest.fixture
def sample_manufacturers_df():
    """Sample manufacturers dataframe for testing."""
    return pd.DataFrame({
        "id": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "name": ["Mfg A", "Mfg B", "Mfg C", "Mfg D", "Mfg E", "Mfg F", "Mfg G", "Mfg H", "Mfg I", "Mfg J"],
        "address": ["Addr 1", None, None, None, None, None, None, None, None, None],  # 90% null
        "comment": [None, None, None, None, None, None, None, None, None, None],  # 100% null
        "representative": [None, None, None, None, None, None, "Rep", None, None, None],  # 90% null
        "updated_at": ["2020-01-01"] * 10,
        "created_at": ["2020-01-01"] * 10,
        "source": ["FDA"] * 10,
        "slug": ["mfg-a", "mfg-b", "mfg-c", "mfg-d", "mfg-e", "mfg-f", "mfg-g", "mfg-h", "mfg-i", "mfg-j"],
    })


@pytest.fixture
def sample_enriched_df(sample_events_df, sample_devices_df, sample_manufacturers_df):
    """Sample enriched dataframe for testing."""
    from src.merge import build_enriched
    enriched, inner, _ = build_enriched(sample_events_df, sample_devices_df, sample_manufacturers_df)
    return enriched