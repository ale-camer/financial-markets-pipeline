import json
from datetime import datetime, date

from src.models.price_models import YFinanceExtractionPayload, YFinanceOHLCVRecord

def test_sqlite_insert_raw_payload(sqlite_loader):
    raw_data = [{"some_key": "some_value"}]
    sqlite_loader.insert_raw_payload(
        ticker="AAPL",
        source="yahoo",
        raw_payload=raw_data,
        extracted_at=datetime(2023, 1, 1, 12, 0)
    )
    
    with sqlite_loader.get_connection() as conn:
        result = conn.execute("SELECT * FROM raw_data").fetchall()
        
    assert len(result) == 1
    row = result[0]
    assert row["ticker"] == "AAPL"
    assert row["source"] == "yahoo"
    assert json.loads(row["payload"]) == raw_data
    assert row["extracted_at"] == "2023-01-01T12:00:00"

def test_sqlite_insert_staging_records(sqlite_loader):
    payload = YFinanceExtractionPayload(
        ticker="AAPL",
        extracted_at=datetime.utcnow(),
        records=[
            YFinanceOHLCVRecord(
                date=date(2023, 1, 1),
                open=150.0,
                high=155.0,
                low=149.0,
                close=154.0,
                volume=1000000,
                dividends=0.0,
                stock_splits=0.0
            )
        ]
    )
    
    # First insert
    sqlite_loader.insert_staging_records(payload)
    
    with sqlite_loader.get_connection() as conn:
        result = conn.execute("SELECT * FROM staging_prices").fetchall()
    assert len(result) == 1
    assert result[0]["close"] == 154.0
    
    # Modify and insert again to test UPSERT
    payload.records[0].close = 160.0
    sqlite_loader.insert_staging_records(payload)
    
    with sqlite_loader.get_connection() as conn:
        result = conn.execute("SELECT * FROM staging_prices").fetchall()
    assert len(result) == 1
    assert result[0]["close"] == 160.0
