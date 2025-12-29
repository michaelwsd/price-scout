"""
Scorptec Scraper with Fallback.

This module implements a web scraper for Scorptec with automatic fallback.
First attempts to use the faster HTTP API scraper, then falls back to the
cloudscraper-based scraper if the HTTP scraper fails.

Classes:
    ScorptecScraper: Fallback scraper for www.scorptec.com.au
"""

import logging
from models.models import PriceResult
from models.base_scraper import BaseScraper
from scrapers.scorptec.scorptec_scraper_http import ScorptecScraper as ScorptecHTTPScraper
from scrapers.scorptec.scorptec_scraper import ScorptecScraper as ScorptecCloudscraperScraper


logger = logging.getLogger(__name__)


class ScorptecScraper(BaseScraper):
    """
    Web scraper for Scorptec with automatic fallback mechanism.

    Attempts to scrape using the faster HTTP API method first. If that fails
    or raises an exception, automatically falls back to the cloudscraper-based
    method for handling Cloudflare protection.

    Attributes:
        vendor_id: Identifier "scorptec"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = ScorptecScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> print(f"Found at: {result.url}")
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
        Scrape price data with automatic fallback between HTTP and cloudscraper methods.

        First attempts to use the HTTP API scraper (faster). If it fails, returns
        a not_found result, or raises an exception, automatically falls back to
        the cloudscraper-based scraper.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with complete product data if found, otherwise not_found result.
        """
        # Try HTTP scraper first (faster)
        try:
            logger.info(f"Scorptec: Attempting HTTP scraper for MPN={mpn}")
            http_scraper = ScorptecHTTPScraper()
            result = await http_scraper.scrape(mpn)

            # If product was found, return the result
            if result.found:
                logger.info(f"Scorptec: HTTP scraper succeeded for MPN={mpn}")
                return result

            # If not found, try fallback
            logger.info(f"Scorptec: HTTP scraper returned not found, trying cloudscraper fallback for MPN={mpn}")

        except Exception as e:
            # On exception, log and try fallback
            logger.warning(f"Scorptec: HTTP scraper failed for MPN={mpn}: {e}")
            logger.info(f"Scorptec: Attempting cloudscraper fallback for MPN={mpn}")

        # Fallback to cloudscraper scraper
        try:
            cloudscraper_scraper = ScorptecCloudscraperScraper()
            result = await cloudscraper_scraper.scrape(mpn)

            if result.found:
                logger.info(f"Scorptec: Cloudscraper fallback succeeded for MPN={mpn}")
            else:
                logger.warning(f"Scorptec: Cloudscraper fallback also returned not found for MPN={mpn}")

            return result

        except Exception as e:
            logger.error(f"Scorptec: Both scrapers failed for MPN={mpn}: {e}")
            return self.not_found
