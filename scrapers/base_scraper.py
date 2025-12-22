from abc import ABC, abstractmethod
from pydantic import BaseModel
from .models import PriceResult

class BaseScraper(BaseModel, ABC):
    vendor_id: str
    base_domains: list[str]
    currency: str

    class Config:
        arbitrary_types_allowed = True 

    @abstractmethod    
    async def search(self, mpn: str) -> list[str]:
        """Return candidate product URLs"""
    
    @abstractmethod
    async def scrape(self, url: str, mpn: str) -> PriceResult:
        """Extract price and metadata"""

    async def run(self, mpn: str) -> list[PriceResult]:
        urls = await self.search(mpn)

        results = []
        for url in urls:
            try:
                result = await self.scrape(url, mpn)
                if result.confidence:
                    results.append(result)
            except Exception:
                continue

        return results