"""
Scorptec Computers Scraper.

This module implements a web scraper for Scorptec Computers, an Australian
computer parts retailer. Uses cloudscraper to bypass Cloudflare protection.

Classes:
    ScorptecScraper: Scraper implementation for www.scorptec.com.au
"""

import cloudscraper
import asyncio
import logging
from bs4 import BeautifulSoup

from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class ScorptecScraper(BaseScraper):
    """
    Web scraper for Scorptec Computers (www.scorptec.com.au).

    Scrapes product prices from Scorptec using their search functionality.
    Implements CloudScraper to handle Cloudflare protection and runs
    synchronous scraping in an async executor for non-blocking operation.

    Attributes:
        vendor_id: Identifier "scorptec"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = ScorptecScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> print(f"${result.price} at {result.url}")
    """

    vendor_id: str = "scorptec"
    currency: str = "AUD"
    not_found: PriceResult = PriceResult(
        vendor_id=vendor_id,
        url=None,
        mpn=None,
        price=None,
        currency=None,
        found=False
    )

    async def scrape(self, mpn: str) -> PriceResult:
        """
        Scrape price data for a given MPN (async wrapper).

        Delegates to scrape_sync() via an async executor to avoid blocking
        the event loop during HTTP requests and HTML parsing.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with product data if found, or not_found result otherwise.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scrape_sync, mpn)

    def scrape_sync(self, mpn: str) -> PriceResult:
        """
        Synchronous scraping implementation.

        Searches Scorptec's website for the MPN, validates the match,
        and extracts price information from the product page.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with vendor_id, url, mpn, price, currency, and found status.
        """
        scraper = cloudscraper.create_scraper()
        url = f"https://www.scorptec.com.au/search/go?w={mpn}&cnt=1"
        
        logger.info("Scraping Scorptec for MPN=%s", mpn)

        try:
            res = scraper.get(url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            return self.not_found

        soup = BeautifulSoup(res.text, "lxml")

        # check if mpn matches
        mpn_div = soup.select_one("div.product-page-model")
        if not mpn_div or mpn_div.get_text(strip=True) != mpn:
            logger.warning(
                "Product not found for MPN=%s on Scorptec page %s",
                mpn,
                url,
            )
            return self.not_found
        
        # check for price
        price_div = soup.select_one("div.product-page-price.product-main-price")
        if not price_div:
            logger.warning(
                "Price not found for MPN=%s on Scorptec page %s",
                mpn,
                url,
            )
            return self.not_found 

        price_text = price_div.get_text(strip=True)
        logger.debug("Raw price text extracted: %s", price_text)

        in_stock = soup.select_one("div.product-page-status.status-box").select_one("span.status-text").get_text() == "in stock"

        return PriceResult(
            vendor_id=self.vendor_id,
            url=url,
            mpn=mpn,
            price=float(price_text),
            currency=self.currency,
            in_stock=in_stock,
            found=True
        )