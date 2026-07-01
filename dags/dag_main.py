import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import our pipeline modules
from src.extractors.alpha_vantage_extractor import AlphaVantageExtractor
from src.extractors.yfinance_extractor import YFinanceExtractor
from src.loaders.db_loader import SQLiteLoader
from src.loaders.postgres_loader import PostgresLoader
from src.models.price_models import (
    YFinanceExtractionPayload,
    YFinanceOHLCVRecord,
)
from src.scripts.load_companies import process_single_ticker
from src.transformers.data_transformer import DataTransformer

logger = logging.getLogger("airflow.task")

# Default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_exponential_backoff": True,
    "retry_delay": timedelta(minutes=2),
    "max_retry_delay": timedelta(minutes=10),
}


def ingest_company_metadata():
    """Ingests company metadata for new tickers into PostgreSQL dim_companies."""
    logger.info("Starting company metadata ingestion...")
    sqlite_loader = SQLiteLoader()
    postgres_loader = PostgresLoader()
    av_extractor = AlphaVantageExtractor()

    sqlite_loader.init_tables()
    postgres_loader.init_tables()

    existing_companies = postgres_loader.get_existing_company_ids()
    yfinance_extractor = YFinanceExtractor()
    tickers = yfinance_extractor.tickers

    tickers_to_process = [t for t in tickers if t.upper() not in existing_companies]
    if not tickers_to_process:
        logger.info("All company metadata already ingested.")
        return

    logger.info(f"Ingesting metadata for: {tickers_to_process}")
    # Process up to 5 tickers per run to avoid rate limits (Alpha Vantage free tier is 5 calls/min)
    import time
    for i, ticker in enumerate(tickers_to_process[:5]):
        logger.info(f"Processing company metadata for {ticker}...")
        success, using_fallback = process_single_ticker(
            ticker, av_extractor, sqlite_loader, postgres_loader
        )
        if success:
            logger.info(f"Successfully processed company: {ticker}")
        else:
            logger.warning(f"Failed to process company: {ticker}")
        
        # Sleep to avoid Alpha Vantage rate limiting if not using fallback
        if i < len(tickers_to_process[:5]) - 1:
            if not using_fallback:
                logger.info("Sleeping 12 seconds to respect Alpha Vantage API limit...")
                time.sleep(12)
            else:
                time.sleep(1)


def extract_and_stage_daily_prices():
    """Extracts daily prices from yfinance, validates with Pydantic, and loads into SQLite staging."""
    logger.info("Starting daily prices extraction...")
    extractor = YFinanceExtractor()
    loader = SQLiteLoader()
    
    loader.init_tables()

    # Define daily date range (last 5 days to capture weekend/holiday gaps and current date)
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=5)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    tickers = extractor.tickers
    extracted_at = datetime.utcnow()

    logger.info(f"Fetching data from {start_str} to {end_str} for tickers: {tickers}")

    for ticker in tickers:
        try:
            records = extractor.fetch_ohlcv(
                ticker=ticker,
                start_date=start_str,
                end_date=end_str,
            )
            if not records:
                logger.warning(f"No records found for ticker {ticker}")
                continue

            # Ingest raw payload
            loader.insert_raw_payload(
                ticker=ticker,
                source="yfinance",
                raw_payload=records,
                extracted_at=extracted_at,
            )

            # Validate and ingest staging records
            payload = YFinanceExtractionPayload(
                ticker=ticker,
                extracted_at=extracted_at,
                records=[YFinanceOHLCVRecord(**r) for r in records],
            )
            loader.insert_staging_records(payload)
            logger.info(f"Successfully staged {len(records)} records for {ticker}")
        except Exception as e:
            logger.error(f"Error staging daily prices for {ticker}: {e}")
            raise


def transform_and_load_curated():
    """Migrates transformed data from SQLite staging to Postgres curated database."""
    logger.info("Starting transformation and load to Postgres...")
    sqlite_loader = SQLiteLoader()
    postgres_loader = PostgresLoader()
    transformer = DataTransformer()

    postgres_loader.init_tables()
    existing_company_ids = postgres_loader.get_existing_company_ids()

    sqlite_conn = sqlite_loader.get_connection()
    cursor = sqlite_conn.cursor()

    try:
        cursor.execute(
            """
            SELECT ticker, date, open, high, low, close, volume,
                   dividends, stock_splits
              FROM staging_prices
            """
        )
        batch_size = 2000
        total_migrated = 0

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break

            # Enforce referential integrity (only migrate if company exists in dim_companies)
            records = [
                dict(row) for row in rows
                if row["ticker"] in existing_company_ids
            ]
            if not records:
                continue

            transformed_prices = transformer.transform_daily_prices(records)
            transformed_dividends = transformer.transform_dividends(records)

            postgres_loader.insert_daily_prices(transformed_prices)
            postgres_loader.insert_dividends(transformed_dividends)
            
            total_migrated += len(records)
            logger.info(f"Migrated {total_migrated} records to Postgres curated tables...")

        logger.info(f"Migration completed. Total records migrated: {total_migrated}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        sqlite_conn.close()


# Define the DAG
with DAG(
    "financial_market_daily_pipeline",
    default_args=default_args,
    description="Daily pipeline to ingest, validate, transform, and load financial market data",
    schedule_interval="@daily",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    tags=["finance", "etl"],
) as dag:

    task_ingest_companies = PythonOperator(
        task_id="ingest_company_metadata",
        python_callable=ingest_company_metadata,
    )

    task_extract_prices = PythonOperator(
        task_id="extract_and_stage_daily_prices",
        python_callable=extract_and_stage_daily_prices,
    )

    task_transform_load = PythonOperator(
        task_id="transform_and_load_curated",
        python_callable=transform_and_load_curated,
    )

    # Establish dependencies
    task_ingest_companies >> task_extract_prices >> task_transform_load
