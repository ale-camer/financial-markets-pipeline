from pydantic import BaseModel, Field


class AlphaVantageCompanyRecord(BaseModel):
    """Pydantic model representing validated company metadata."""

    symbol: str = Field(..., alias="Symbol", min_length=1)
    name: str = Field(..., alias="Name", min_length=1)
    sector: str = Field("Unknown", alias="Sector")
    industry: str = Field("Unknown", alias="Industry")
    currency: str = Field("USD", alias="Currency")

    model_config = {
        "populate_by_name": True,
    }
