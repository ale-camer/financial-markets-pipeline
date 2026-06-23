import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from src.loaders.db_loader import SQLiteLoader
from src.loaders.postgres_loader import PostgresLoader

@pytest.fixture
def sqlite_loader(tmp_path):
    """Provides a SQLiteLoader instance pointed to a temporary file."""
    db_path = tmp_path / "test_market_data.db"
    loader = SQLiteLoader(db_path=str(db_path))
    loader.init_tables()
    yield loader

@pytest.fixture
def postgres_loader():
    """Provides a PostgresLoader instance pointed to a dynamically created test database."""
    # Base credentials from env or defaults (matching docker-compose)
    host = os.getenv("CURATED_POSTGRES_HOST", "postgres")
    port = int(os.getenv("CURATED_POSTGRES_PORT", 5432))
    user = os.getenv("CURATED_POSTGRES_USER", "airflow")
    password = os.getenv("CURATED_POSTGRES_PASSWORD", "airflow")
    base_db = os.getenv("CURATED_POSTGRES_DB", "airflow")

    # Generate a unique test database name
    test_db_name = f"test_db_{uuid.uuid4().hex[:8]}"

    # Connect to the base database with AUTOCOMMIT to create the new test DB
    base_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{base_db}"
    engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))

    original_db_env = os.getenv("CURATED_POSTGRES_DB")
    original_host_env = os.getenv("CURATED_POSTGRES_HOST")
    
    try:
        # Temporarily override the environment variable so PostgresLoader connects to the test DB
        os.environ["CURATED_POSTGRES_DB"] = test_db_name
        os.environ["CURATED_POSTGRES_HOST"] = host

        loader = PostgresLoader()
        loader.init_tables()
        
        yield loader
        
        # Clean up connections so we can drop the DB
        loader.engine.dispose()
    finally:
        # Restore environment variables
        if original_db_env is not None:
            os.environ["CURATED_POSTGRES_DB"] = original_db_env
        else:
            del os.environ["CURATED_POSTGRES_DB"]
            
        if original_host_env is not None:
            os.environ["CURATED_POSTGRES_HOST"] = original_host_env
        else:
            if "CURATED_POSTGRES_HOST" in os.environ:
                del os.environ["CURATED_POSTGRES_HOST"]
            
        # Drop the test database
        with engine.connect() as conn:
            # Terminate other connections if any exist
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                  AND pid <> pg_backend_pid();
            """))
            conn.execute(text(f"DROP DATABASE {test_db_name}"))
        
        engine.dispose()
