from abc import ABC, abstractmethod
from pydantic import BaseModel
from .models import PriceResult

class BaseScraper(BaseModel, ABC):
    vendor_id: str
    currency: str

    class Config:
        arbitrary_types_allowed = True 
    
    @abstractmethod
    async def scrape(self, url: str, mpn: str) -> PriceResult:
        """Extract price and metadata"""