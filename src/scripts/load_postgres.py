import logging

from src.loaders.db_loader import SQLiteLoader
from src.loaders.postgres_loader import PostgresLoader
from src.transformers.data_transformer import DataTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_data():
    """Migrates all records from SQLite staging to Postgres curated."""
    sqlite_loader = SQLiteLoader()
    postgres_loader = PostgresLoader()
    transformer = DataTransformer()

    logger.info("Initializing Postgres tables...")
    postgres_loader.init_tables()

    logger.info("Reading data from SQLite staging_prices...")
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
        batch_size = 5000
        total_migrated = 0

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break

            # Enforce referential integrity
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
            logger.info(
                f"Migrated {total_migrated} records to Postgres..."
            )

        logger.info(
            f"Migration completed. "
            f"Total records migrated: {total_migrated}"
        )
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    migrate_data()
