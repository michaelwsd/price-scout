import cloudscraper
import asyncio
import logging
from bs4 import BeautifulSoup

from type.models import PriceResult
from type.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class MwaveScraper(BaseScraper):
    vendor_id: str = "mwave"
    currency: str = "AUD" 

    async def scrape(self, mpn: str) -> PriceResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scrape_sync, mpn)
    
    def scrape_sync(self, mpn: str) -> PriceResult:
        scraper = cloudscraper.create_scraper()
        url = f"https://www.mwave.com.au/searchresult?button=go&w={mpn}&cnt=1"
        
        logger.info("Scraping Mwave for MPN=%s", mpn)

        try:
            res = scraper.get(url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            return None

        soup = BeautifulSoup(res.text, "lxml")

        # check if mpn matches
        mpn_div = soup.select_one("span.sku")
        if not mpn_div or mpn_div.get_text().split()[-1] != mpn:
            logger.warning(
                "Product not found for MPN=%s on Mwave page %s",
                mpn,
                url,
            )
            return None
        
        # check for price
        price_div = soup.select_one("div.divPriceNormal")
        if not price_div:
            logger.warning(
                "Price not found for MPN=%s on Mwave page %s",
                mpn,
                url,
            )
            return None

        price_text = price_div.get_text().strip().replace(",", "")[1:]
        logger.debug("Raw price text extracted: %s", price_text)

        return PriceResult(
            vendor_id=self.vendor_id,
            url=url,
            mpn=mpn,
            price=price_text,
            currency=self.currency,
        )