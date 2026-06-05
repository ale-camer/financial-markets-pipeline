from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.db_models import Base, DimCompany, FctDailyPrice, FctDividend


@pytest.fixture
def db_session():
    """Provides an in-memory SQLite database session for model validation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_dim_company_creation(db_session):
    """Verifies that DimCompany records can be inserted and retrieved."""
    company = DimCompany(
        company_id="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        currency="USD",
    )
    db_session.add(company)
    db_session.commit()

    retrieved = (
        db_session.query(DimCompany).filter_by(company_id="AAPL").first()
    )
    assert retrieved is not None
    assert retrieved.name == "Apple Inc."
    assert retrieved.sector == "Technology"
    assert isinstance(retrieved.updated_at, datetime)


def test_fct_daily_price_creation(db_session):
    """Verifies that FctDailyPrice records can be inserted and retrieved."""
    company = DimCompany(
        company_id="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        currency="USD",
    )
    db_session.add(company)
    db_session.commit()

    price = FctDailyPrice(
        ticker="AAPL",
        date=date(2026, 6, 1),
        open=100.0,
        high=105.0,
        low=99.0,
        close=102.5,
        volume=1000000,
    )
    db_session.add(price)
    db_session.commit()

    retrieved = db_session.query(FctDailyPrice).filter_by(ticker="AAPL").first()
    assert retrieved is not None
    assert retrieved.close == 102.5
    assert retrieved.date == date(2026, 6, 1)


def test_fct_dividend_creation(db_session):
    """Verifies that FctDividend records can be inserted and retrieved."""
    company = DimCompany(
        company_id="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        currency="USD",
    )
    db_session.add(company)
    db_session.commit()

    div = FctDividend(
        ticker="AAPL",
        date=date(2026, 6, 1),
        dividends=0.25,
        stock_splits=0.0,
    )
    db_session.add(div)
    db_session.commit()

    retrieved = db_session.query(FctDividend).filter_by(ticker="AAPL").first()
    assert retrieved is not None
    assert retrieved.dividends == 0.25
    assert retrieved.stock_splits == 0.0
