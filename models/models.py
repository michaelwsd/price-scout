import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field 
from decimal import Decimal

class PriceResult(BaseModel):
    vendor_id: str 
    url: Optional[HttpUrl] = None
    mpn: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    scraped_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    found: bool 