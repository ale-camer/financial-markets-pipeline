import os
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values


class PostgresLoader:
    """Manages connection, table creation, and bulk upserts in Postgres."""

    def __init__(self):
        # Database connection defaults (configured in docker-compose / .env)
        self.host = "postgres"
        self.port = int(os.getenv("CURATED_POSTGRES_PORT", 5432))
        self.user = os.getenv("CURATED_POSTGRES_USER", "postgres")
        self.password = os.getenv(
            "CURATED_POSTGRES_PASSWORD", "postgres_secure_pass"
        )
        self.database = os.getenv(
            "CURATED_POSTGRES_DB", "market_data"
        )

    def get_connection(self):
        """Creates and returns a connection to the Postgres database."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
        )

    def init_tables(self):
        """Creates curated tables in PostgreSQL if they do not exist."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS curated_prices (
                ticker VARCHAR(10) NOT NULL,
                date DATE NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume BIGINT NOT NULL,
                dividends DOUBLE PRECISION NOT NULL,
                stock_splits DOUBLE PRECISION NOT NULL,
                inserted_at TIMESTAMP NOT NULL,
                PRIMARY KEY (ticker, date)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS dim_companies (
                company_id VARCHAR(12) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                sector VARCHAR(100) NOT NULL,
                industry VARCHAR(100) NOT NULL,
                currency VARCHAR(3) NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
            """,
        ]
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for query in queries:
                    cur.execute(query)
            conn.commit()

    def insert_curated_records(self, records: list[dict]):
        """Performs a bulk UPSERT into curated_prices table."""
        if not records:
            return

        inserted_at = datetime.utcnow()
        data = [
            (
                r["ticker"],
                r["date"],
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                r["volume"],
                r["dividends"],
                r["stock_splits"],
                inserted_at,
            )
            for r in records
        ]

        query = """
            INSERT INTO curated_prices (
                ticker, date, open, high, low, close, volume,
                dividends, stock_splits, inserted_at
            ) VALUES %s
            ON CONFLICT (ticker, date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                dividends = EXCLUDED.dividends,
                stock_splits = EXCLUDED.stock_splits,
                inserted_at = EXCLUDED.inserted_at
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, data)
            conn.commit()

    def insert_companies(self, companies: list[dict]):
        """Performs a bulk UPSERT into dim_companies table."""
        if not companies:
            return

        updated_at = datetime.utcnow()
        data = [
            (
                c["symbol"].upper(),
                c["name"],
                c["sector"],
                c["industry"],
                c["currency"],
                updated_at,
            )
            for c in companies
        ]

        query = """
            INSERT INTO dim_companies (
                company_id, name, sector, industry, currency, updated_at
            ) VALUES %s
            ON CONFLICT (company_id) DO UPDATE SET
                name = EXCLUDED.name,
                sector = EXCLUDED.sector,
                industry = EXCLUDED.industry,
                currency = EXCLUDED.currency,
                updated_at = EXCLUDED.updated_at
        """

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, data)
            conn.commit()

    def get_existing_company_ids(self) -> set[str]:
        """Returns set of company_ids already present in dim_companies."""
        query = "SELECT company_id FROM dim_companies"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    rows = cur.fetchall()
                    return {row[0] for row in rows}
        except Exception:
            # Let's import logging inside or use global logger if defined
            # (there is no logger defined in postgres_loader, so print or log)
            return set()


