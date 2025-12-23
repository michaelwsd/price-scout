from abc import ABC, abstractmethod
from pydantic import BaseModel
from .models import PriceResult

class BaseScraper(BaseModel, ABC):
    vendor_id: str
    currency: str

    class Config:
        arbitrary_types_allowed = True 

    @abstractmethod
    def scrape(self, mpn: str) -> PriceResult:
        """Extract price and metadata"""

    def clean_mpn(self, mpn: str) -> str:
        return mpn.strip().replace("/", "-")