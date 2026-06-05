from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DimCompany(Base):
    __tablename__ = "dim_companies"

    company_id = Column(String(12), primary_key=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=False)
    industry = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    daily_prices = relationship(
        "FctDailyPrice",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    dividends = relationship(
        "FctDividend",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<DimCompany(company_id='{self.company_id}', "
            f"name='{self.name}')>"
        )


class FctDailyPrice(Base):
    __tablename__ = "fct_daily_prices"

    ticker = Column(
        String(10),
        ForeignKey("dim_companies.company_id", ondelete="CASCADE"),
        primary_key=True,
    )
    date = Column(Date, primary_key=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    inserted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    company = relationship("DimCompany", back_populates="daily_prices")

    def __repr__(self) -> str:
        return (
            f"<FctDailyPrice(ticker='{self.ticker}', "
            f"date='{self.date}', close={self.close})>"
        )


class FctDividend(Base):
    __tablename__ = "fct_dividends"

    ticker = Column(
        String(10),
        ForeignKey("dim_companies.company_id", ondelete="CASCADE"),
        primary_key=True,
    )
    date = Column(Date, primary_key=True)
    dividends = Column(Float, nullable=False)
    stock_splits = Column(Float, nullable=False)
    inserted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    company = relationship("DimCompany", back_populates="dividends")

    def __repr__(self) -> str:
        return (
            f"<FctDividend(ticker='{self.ticker}', date='{self.date}', "
            f"dividends={self.dividends})>"
        )
