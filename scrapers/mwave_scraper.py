"""
Mwave Australia Scraper.

This module implements a web scraper for Mwave Australia, an Australian
computer parts and electronics retailer. Uses cloudscraper for Cloudflare bypass.

Classes:
    MwaveScraper: Scraper implementation for www.mwave.com.au
"""

import cloudscraper
import asyncio
import logging
from bs4 import BeautifulSoup

from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class MwaveScraper(BaseScraper):
    """
    Web scraper for Mwave Australia (www.mwave.com.au).

    Scrapes product prices from Mwave using their search functionality.
    Validates MPN matches and extracts pricing from the search results page.

    Attributes:
        vendor_id: Identifier "mwave"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = MwaveScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> if result.found:
        ...     print(f"${result.price}")
    """

    vendor_id: str = "mwave"
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

        Searches Mwave's website, validates MPN match in SKU field,
        and extracts price from the search results.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with vendor_id, url, mpn, price, currency, and found status.
        """
        scraper = cloudscraper.create_scraper()
        url = f"https://www.mwave.com.au/searchresult?button=go&w={mpn}&cnt=1"

        logger.info("Scraping Mwave for MPN=%s", mpn)

        try:
            res = scraper.get(url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            return self.not_found

        soup = BeautifulSoup(res.text, "lxml")

        # check if mpn matches
        mpn_div = soup.select_one("span.sku")
        if not mpn_div or mpn_div.get_text(strip=True).split()[-1] != mpn:
            logger.warning(
                "Product not found for MPN=%s on Mwave page %s",
                mpn,
                url,
            )
            return self.not_found

        # check for price
        price_div = soup.select_one("div.divPriceNormal")
        if not price_div:
            logger.warning(
                "Price not found for MPN=%s on Mwave page %s",
                mpn,
                url,
            )
            return self.not_found

        price_text = price_div.get_text(strip=True).replace(",", "")[1:]
        logger.debug("Raw price text extracted: %s", price_text)

        return PriceResult(
            vendor_id=self.vendor_id,
            url=url,
            mpn=mpn,
            price=float(price_text),
            currency=self.currency,
            found=True
        )
