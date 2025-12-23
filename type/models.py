import datetime
from pydantic import BaseModel, HttpUrl, Field 
from decimal import Decimal

class PriceResult(BaseModel):
    vendor_id: str 
    url: HttpUrl
    mpn: str
    price: Decimal
    currency: str
    scraped_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))