"""
Digicor Australia Scraper.

This module implements a web scraper for Digicor Australia, an Australian
computer parts and electronics retailer. Uses cloudscraper for Cloudflare bypass.

Classes:
    DigicorScraper: Scraper implementation for www.digicor.com.au
"""

import cloudscraper
import asyncio
import logging
from bs4 import BeautifulSoup

from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class DigicorScraper(BaseScraper):
    """
    Web scraper for Digicor Australia (www.digicor.com.au).

    Scrapes product prices from Digicor using their search functionality.
    Validates MPN matches and extracts pricing from the search results page.

    Attributes:
        vendor_id: Identifier "digicor"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = DigicorScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> if result.found:
        ...     print(f"${result.price}")
    """

    vendor_id: str = "digicor"
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

        Searches Digicor's website, validates MPN match in SKU field,
        and extracts price from the search results.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with vendor_id, url, mpn, price, currency, and found status.
        """
        scraper = cloudscraper.create_scraper()
        url = f"https://www.digicor.com.au/catalogsearch/result/?q={mpn}"

        logger.info("Scraping Digicor for MPN=%s", mpn)

        try:
            res = scraper.get(url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            return self.not_found

        soup = BeautifulSoup(res.text, "lxml")

        product_element = soup.select_one("form.product-item")

        if not product_element:
            logger.warning(
                "Product not found for MPN=%s on Digicor page %s",
                mpn,
                url,
            )
            return self.not_found
        
        model_element = product_element.select_one("li").get_text().split()[-1]

        if model_element != mpn:
            logger.warning(
                "Product not found for MPN=%s on Digicor page %s",
                mpn,
                url,
            )
            return self.not_found

        price_text = product_element.select_one("span.price").get_text()[2:]
        image = product_element.select_one("a.product.photo")
        url = image['href']
        in_stock = image.select_one("span").get_text().strip() == "In Stock"

        logger.debug("Raw price text extracted: %s", price_text)

        return PriceResult(
            vendor_id=self.vendor_id,
            url=url,
            mpn=mpn,
            price=float(price_text),
            currency=self.currency,
            in_stock=in_stock,
            found=True
        )
