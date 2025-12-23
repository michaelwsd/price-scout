from bs4 import BeautifulSoup
import cloudscraper
import logging
from type.base_scraper import BaseScraper
from type.models import PriceResult

logger = logging.getLogger(__name__)

class ScorptecScraper(BaseScraper):
    vendor_id: str = "scorptec"
    currency: str = "AUD" 

    def scrape(self, mpn: str) -> PriceResult:
        url = f"https://www.scorptec.com.au/search/go?w={mpn}&cnt=1"
        logger.info("Scraping Scorptec for MPN=%s", mpn)

        scraper = cloudscraper.create_scraper()

        try:
            res = scraper.get(url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            raise

        soup = BeautifulSoup(res.text, "lxml")

        # check if mpn matches
        mpn_div = soup.select_one("div.product-page-model")
        if not mpn_div or mpn_div.get_text(strip=True) != mpn:
            logger.warning(
                "Product not found for MPN=%s on Scorptec page %s",
                mpn,
                url,
            )
            raise ValueError("Product not found")
        
        # check for price
        price_div = soup.select_one("div.product-page-price.product-main-price")
        if not price_div:
            logger.warning(
                "Price not found for MPN=%s on Scorptec page %s",
                mpn,
                url,
            )
            raise ValueError("Price element not found")

        price_text = price_div.get_text(strip=True)
        logger.debug("Raw price text extracted: %s", price_text)

        return PriceResult(
            vendor_id=self.vendor_id,
            url=url,
            mpn=mpn,
            price=price_text,
            currency=self.currency,
        )