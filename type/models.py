from pydantic import BaseModel, HttpUrl, Field 
from decimal import Decimal
from datetime import datetime

class PriceResult(BaseModel):
    vendor_id: str 
    url: HttpUrl
    mpn: str
    price: Decimal
    currency: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

class SearchResult(BaseModel):
    vendor_id: str
    urls: list[HttpUrl]
    