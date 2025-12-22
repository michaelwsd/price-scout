from pydantic import BaseModel, HttpUrl, Field 
from decimal import Decimal
from datetime import datetime

class PriceResult(BaseModel):
    vendor_id: str 
    url: HttpUrl
    mpn: str
    price: Decimal
    currency: str
    in_stock: bool 
    confident: bool = Field(default_factory=False)
    scraped_at: datetime = Field(default_factory=datetime.now())

class SearchResult(BaseModel):
    vendor_id: str
    urls: list[HttpUrl]
    