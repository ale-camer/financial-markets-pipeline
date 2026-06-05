import json
import os
import sqlite3
from datetime import datetime

from src.models.price_models import YFinanceExtractionPayload


class SQLiteLoader:
    """Manages raw/staging schema init and data loading in SQLite."""

    def __init__(self, db_path: str = "data/market_data.db"):
        self.db_path = db_path
        # Ensure directories exist
        if os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_tables(self):
        """Initializes raw and staging tables if they do not exist."""
        with self.get_connection() as conn:
            # Raw layer: Store raw JSON responses directly from APIs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    extracted_at TEXT NOT NULL
                )
            """)

            # Staging layer: Typed, validated data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS staging_prices (
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    dividends REAL NOT NULL,
                    stock_splits REAL NOT NULL,
                    inserted_at TEXT NOT NULL,
                    PRIMARY KEY (ticker, date)
                )
            """)
            conn.commit()

    def insert_raw_payload(
        self,
        ticker: str,
        source: str,
        raw_payload: list[dict],
        extracted_at: datetime,
    ):
        """Inserts raw JSON data into the raw_data table."""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO raw_data "
                "(ticker, source, payload, extracted_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    ticker,
                    source,
                    json.dumps(raw_payload),
                    extracted_at.isoformat(),
                ),
            )
            conn.commit()

    def insert_staging_records(self, payload: YFinanceExtractionPayload):
        """Inserts validated records into staging_prices using UPSERT."""
        inserted_at = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            for record in payload.records:
                conn.execute(
                    """
                    INSERT INTO staging_prices (
                        ticker, date, open, high, low, close, volume,
                        dividends, stock_splits, inserted_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, date) DO UPDATE SET
                        open=excluded.open,
                        high=excluded.high,
                        low=excluded.low,
                        close=excluded.close,
                        volume=excluded.volume,
                        dividends=excluded.dividends,
                        stock_splits=excluded.stock_splits,
                        inserted_at=excluded.inserted_at
                    """,
                    (
                        payload.ticker,
                        record.date.isoformat(),
                        record.open,
                        record.high,
                        record.low,
                        record.close,
                        record.volume,
                        record.dividends,
                        record.stock_splits,
                        inserted_at,
                    ),
                )
            conn.commit()
