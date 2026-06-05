from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class YFinanceOHLCVRecord(BaseModel):
    """Pydantic model representing a single daily stock price record."""

    date: date
    open: float = Field(
        ..., gt=0, description="Opening price of the day, must be positive"
    )
    high: float = Field(
        ..., gt=0, description="Highest price of the day, must be positive"
    )
    low: float = Field(
        ..., gt=0, description="Lowest price of the day, must be positive"
    )
    close: float = Field(
        ..., gt=0, description="Closing price of the day, must be positive"
    )
    volume: int = Field(
        ..., ge=0, description="Volume of transactions, must be non-negative"
    )
    dividends: float = Field(
        default=0.0, ge=0.0, description="Dividends paid, must be non-negative"
    )
    stock_splits: float = Field(
        default=0.0,
        ge=0.0,
        description="Stock splits ratio, must be non-negative",
    )

    @field_validator("high")
    @classmethod
    def check_high_prices(cls, v: float, info) -> float:
        # Pydantic v2 validation context is in info.data
        if "open" in info.data and v < info.data["open"]:
            raise ValueError(
                f"High price ({v}) cannot be lower than open price "
                f"({info.data['open']})"
            )
        if "close" in info.data and v < info.data["close"]:
            raise ValueError(
                f"High price ({v}) cannot be lower than close price "
                f"({info.data['close']})"
            )
        return v

    @field_validator("low")
    @classmethod
    def check_low_prices(cls, v: float, info) -> float:
        if "open" in info.data and v > info.data["open"]:
            raise ValueError(
                f"Low price ({v}) cannot be higher than open price "
                f"({info.data['open']})"
            )
        if "close" in info.data and v > info.data["close"]:
            raise ValueError(
                f"Low price ({v}) cannot be higher than close price "
                f"({info.data['close']})"
            )
        if "high" in info.data and v > info.data["high"]:
            raise ValueError(
                f"Low price ({v}) cannot be higher than high price "
                f"({info.data['high']})"
            )
        return v


class YFinanceExtractionPayload(BaseModel):
    """Pydantic model representing the extraction payload for a ticker."""

    ticker: str = Field(..., min_length=1, description="Stock ticker symbol")
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of when extraction was run",
    )
    records: list[YFinanceOHLCVRecord] = Field(
        ..., description="List of validated stock price records"
    )
