from datetime import date, datetime

import pandas as pd
import pytest
from pydantic import ValidationError

from src.extractors.yfinance_extractor import YFinanceExtractor
from src.loaders.db_loader import SQLiteLoader
from src.models.price_models import (
    YFinanceExtractionPayload,
    YFinanceOHLCVRecord,
)

# --- Model Tests ---


def test_ohlcv_record_validation_success():
    data = {
        "date": "2026-06-04",
        "open": 100.0,
        "high": 105.0,
        "low": 98.0,
        "close": 102.0,
        "volume": 1000000,
        "dividends": 0.5,
        "stock_splits": 0.0,
    }
    record = YFinanceOHLCVRecord(**data)
    assert record.date == date(2026, 6, 4)
    assert record.open == 100.0
    assert record.high == 105.0
    assert record.low == 98.0
    assert record.close == 102.0
    assert record.volume == 1000000
    assert record.dividends == 0.5
    assert record.stock_splits == 0.0


def test_ohlcv_record_validation_failure_negative():
    with pytest.raises(ValidationError):
        # Open price cannot be negative
        YFinanceOHLCVRecord(
            date=date(2026, 6, 4),
            open=-100.0,
            high=105.0,
            low=98.0,
            close=102.0,
            volume=1000000,
        )


def test_ohlcv_record_validation_failure_high_prices():
    with pytest.raises(ValidationError):
        # High cannot be lower than open
        YFinanceOHLCVRecord(
            date=date(2026, 6, 4),
            open=100.0,
            high=95.0,
            low=90.0,
            close=98.0,
            volume=1000000,
        )


def test_ohlcv_record_validation_failure_low_prices():
    with pytest.raises(ValidationError):
        # Low cannot be higher than open
        YFinanceOHLCVRecord(
            date=date(2026, 6, 4),
            open=100.0,
            high=105.0,
            low=102.0,
            close=98.0,
            volume=1000000,
        )


# --- Extractor Tests ---


def test_yfinance_extractor_success(mocker):
    # Mock yfinance Ticker and its history method
    mock_ticker = mocker.patch("yfinance.Ticker")

    # Create a dummy DataFrame to return from history()
    mock_df = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [98.0],
            "Close": [102.0],
            "Volume": [1000000],
            "Dividends": [0.0],
            "Stock Splits": [0.0],
        },
        index=pd.DatetimeIndex(["2026-06-04"]),
    )
    mock_ticker.return_value.history.return_value = mock_df

    extractor = YFinanceExtractor(tickers=["AAPL"])
    data = extractor.fetch_ohlcv("AAPL", period="1d")

    assert len(data) == 1
    assert data[0]["date"] == "2026-06-04"
    assert data[0]["open"] == 100.0
    assert data[0]["high"] == 105.0
    assert data[0]["low"] == 98.0
    assert data[0]["close"] == 102.0
    assert data[0]["volume"] == 1000000


def test_yfinance_extractor_empty(mocker):
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_ticker.return_value.history.return_value = pd.DataFrame()

    extractor = YFinanceExtractor(tickers=["AAPL"])
    data = extractor.fetch_ohlcv("AAPL", period="1d")

    assert data == []


# --- SQLite Loader Tests ---


def test_sqlite_loader_workflow(tmp_path):
    db_file = tmp_path / "test_market_data.db"
    loader = SQLiteLoader(db_path=str(db_file))

    # Initialize tables
    loader.init_tables()

    # Test inserting raw payload
    raw_payload = [
        {
            "date": "2026-06-04",
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 102.0,
            "volume": 1000000,
            "dividends": 0.0,
            "stock_splits": 0.0,
        }
    ]
    extracted_at = datetime.utcnow()
    loader.insert_raw_payload("AAPL", "yfinance", raw_payload, extracted_at)

    # Verify raw database entry
    with loader.get_connection() as conn:
        row = conn.execute("SELECT * FROM raw_data").fetchone()
        assert row is not None
        assert row["ticker"] == "AAPL"
        assert row["source"] == "yfinance"
        assert "open" in row["payload"]
        assert row["extracted_at"] == extracted_at.isoformat()

    # Test inserting staging records
    payload = YFinanceExtractionPayload(
        ticker="AAPL",
        extracted_at=extracted_at,
        records=[YFinanceOHLCVRecord(**raw_payload[0])],
    )
    loader.insert_staging_records(payload)

    # Verify staging database entry
    with loader.get_connection() as conn:
        row = conn.execute("SELECT * FROM staging_prices").fetchone()
        assert row is not None
        assert row["ticker"] == "AAPL"
        assert row["date"] == "2026-06-04"
        assert row["open"] == 100.0
        assert row["high"] == 105.0
        assert row["low"] == 98.0
        assert row["close"] == 102.0
        assert row["volume"] == 1000000
        assert row["dividends"] == 0.0
        assert row["stock_splits"] == 0.0
        assert row["inserted_at"] is not None
