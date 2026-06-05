import os
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from src.models.db_models import Base, DimCompany, FctDailyPrice, FctDividend


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

        # Build SQLAlchemy engine and session factory
        self.db_url = (
            f"postgresql+psycopg2://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def init_tables(self):
        """Creates curated tables in PostgreSQL if they do not exist."""
        Base.metadata.create_all(self.engine)

    def insert_daily_prices(self, records: list[dict]):
        """Performs a bulk UPSERT into fct_daily_prices table."""
        if not records:
            return

        inserted_at = datetime.utcnow()
        data = [
            {
                "ticker": r["ticker"],
                "date": r["date"],
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": r["volume"],
                "inserted_at": inserted_at,
            }
            for r in records
        ]

        stmt = insert(FctDailyPrice).values(data)
        update_dict = {
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "inserted_at": stmt.excluded.inserted_at,
        }
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "date"], set_=update_dict
        )

        with self.SessionLocal() as session:
            session.execute(upsert_stmt)
            session.commit()

    def insert_dividends(self, records: list[dict]):
        """Performs a bulk UPSERT into fct_dividends table."""
        if not records:
            return

        inserted_at = datetime.utcnow()
        data = [
            {
                "ticker": r["ticker"],
                "date": r["date"],
                "dividends": r["dividends"],
                "stock_splits": r["stock_splits"],
                "inserted_at": inserted_at,
            }
            for r in records
        ]

        stmt = insert(FctDividend).values(data)
        update_dict = {
            "dividends": stmt.excluded.dividends,
            "stock_splits": stmt.excluded.stock_splits,
            "inserted_at": stmt.excluded.inserted_at,
        }
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["ticker", "date"], set_=update_dict
        )

        with self.SessionLocal() as session:
            session.execute(upsert_stmt)
            session.commit()

    def insert_companies(self, companies: list[dict]):
        """Performs a bulk UPSERT into dim_companies table."""
        if not companies:
            return

        updated_at = datetime.utcnow()
        data = [
            {
                "company_id": c["company_id"],
                "name": c["name"],
                "sector": c["sector"],
                "industry": c["industry"],
                "currency": c["currency"],
                "updated_at": updated_at,
            }
            for c in companies
        ]

        stmt = insert(DimCompany).values(data)
        update_dict = {
            "name": stmt.excluded.name,
            "sector": stmt.excluded.sector,
            "industry": stmt.excluded.industry,
            "currency": stmt.excluded.currency,
            "updated_at": stmt.excluded.updated_at,
        }
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["company_id"], set_=update_dict
        )

        with self.SessionLocal() as session:
            session.execute(upsert_stmt)
            session.commit()

    def get_existing_company_ids(self) -> set[str]:
        """Returns set of company_ids already present in dim_companies."""
        try:
            with self.SessionLocal() as session:
                results = session.query(DimCompany.company_id).all()
                return {r[0] for r in results}
        except Exception:
            return set()

    def insert_curated_records(self, records: list[dict]):
        """Backward-compatible wrapper to insert daily prices and dividends."""
        self.insert_daily_prices(records)
        self.insert_dividends(records)


