import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.extractors.yfinance_extractor import YFinanceExtractor
from src.loaders.db_loader import SQLiteLoader
from src.loaders.postgres_loader import PostgresLoader
from src.models.price_models import (
    YFinanceExtractionPayload,
    YFinanceOHLCVRecord,
)
from src.transformers.data_transformer import DataTransformer

logger = logging.getLogger(__name__)


def init_db():
    """Initialise SQLite database tables."""
    loader = SQLiteLoader()
    loader.init_tables()
    logger.info("SQLite database tables initialised.")


def extract_and_load(logical_date, **kwargs):
    """Fetch previous day's stock data, validate, and load to SQLite."""
    # Use logical_date to extract data for a specific day deterministically.
    start_str = logical_date.strftime("%Y-%m-%d")
    end_str = (logical_date + timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info(
        f"Extracting stock data from {start_str} to {end_str}"
    )
    extractor = YFinanceExtractor()
    loader = SQLiteLoader()

    extracted_at = datetime.utcnow()

    for ticker in extractor.tickers:
        try:
            records = extractor.fetch_ohlcv(
                ticker=ticker,
                start_date=start_str,
                end_date=end_str,
            )
            if not records:
                logger.warning(
                    f"No records found for {ticker} on {start_str}"
                )
                continue

            # Ingest to raw database layer
            loader.insert_raw_payload(
                ticker, "yfinance", records, extracted_at
            )

            # Validate with Pydantic and ingest to staging
            payload = YFinanceExtractionPayload(
                ticker=ticker,
                extracted_at=extracted_at,
                records=[YFinanceOHLCVRecord(**r) for r in records],
            )
            loader.insert_staging_records(payload)
            logger.info(f"Successfully loaded staging data for {ticker}")
        except Exception as e:
            logger.warning(
                f"Failed to extract/load ticker {ticker}: {e}"
            )


def load_to_postgres(logical_date, **kwargs):
    """Load staging data from SQLite to PostgreSQL curated tables."""
    date_str = logical_date.strftime("%Y-%m-%d")
    logger.info(f"Loading staging data to Postgres for date {date_str}")

    sqlite_loader = SQLiteLoader()
    postgres_loader = PostgresLoader()
    transformer = DataTransformer()

    postgres_loader.init_tables()

    conn = sqlite_loader.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT ticker, date, open, high, low, close, volume,
                   dividends, stock_splits
              FROM staging_prices
             WHERE date = ?
            """,
            (date_str,),
        )
        rows = cursor.fetchall()
        existing_company_ids = postgres_loader.get_existing_company_ids()
        records = [
            dict(row) for row in rows
            if row["ticker"] in existing_company_ids
        ]

        if not records:
            logger.info("No valid staging records for Postgres migration.")
            return

        transformed_prices = transformer.transform_daily_prices(records)
        transformed_dividends = transformer.transform_dividends(records)

        postgres_loader.insert_daily_prices(transformed_prices)
        postgres_loader.insert_dividends(transformed_dividends)
        logger.info(
            f"Successfully loaded {len(records)} records to Postgres."
        )
    finally:
        conn.close()


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "market_data_pipeline",
    default_args=default_args,
    description="Daily Yahoo Finance prices extraction and SQLite ingestion",
    schedule="@daily",
    start_date=datetime(2026, 6, 1),
    catchup=False,
) as dag:

    init_db_task = PythonOperator(
        task_id="init_db",
        python_callable=init_db,
    )

    extract_and_load_task = PythonOperator(
        task_id="extract_and_load_daily",
        python_callable=extract_and_load,
    )

    load_to_postgres_task = PythonOperator(
        task_id="load_to_postgres",
        python_callable=load_to_postgres,
    )

    init_db_task >> extract_and_load_task >> load_to_postgres_task
