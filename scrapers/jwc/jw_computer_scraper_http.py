"""
JW Computers HTTP API Scraper.

This module implements a web scraper for JW Computers using their Algolia search API.
Bypasses the need for browser automation by directly querying the search API endpoint.

Classes:
    JWComputersScraper: API-based scraper for www.jw.com.au
"""

import logging
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class JWComputersScraper(BaseScraper):
    """
    Web scraper for JW Computers (www.jw.com.au) using Algolia API.

    Queries JW Computers' Algolia search backend directly for faster,
    more reliable scraping without browser automation overhead.

    Implementation Notes:
        - Uses public Algolia API keys extracted from website
        - Leverages curl_cffi for browser TLS fingerprinting
        - Avoids Playwright/Selenium overhead

    Attributes:
        vendor_id: Identifier "jw_computers"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = JWComputersScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> print(f"Found at: {result.url}")
    """

    vendor_id: str = "jw_computers"
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
        Scrape price data by querying Algolia search API.

        Constructs an Algolia API request for the MPN, validates the result,
        and extracts price and URL information from the JSON response.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with complete product data if found, otherwise not_found result.
        """
        # JW Computers uses the Algolia search engine API
        url = "https://catalog.jw.com.au/1/indexes/*/queries"

        # Algolia API keys (public keys extracted from the website network traffic)
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "x-algolia-api-key": "ODA4MDI2NDg3OWI5MTFmNTNhNWUzYzAxMmFjZThiMzQxOGQ1ZDhlOTRhZDI1YWQwNjM4NDA3MmU5YTU1NjEyZHRhZ0ZpbHRlcnM9JnZhbGlkVW50aWw9MTc2NjcwNTI3OA==",
            "x-algolia-application-id": "KDNP96B3XK",
        }

        # Construct the query payload
        # We target the "m2live_default_products" index and request only 1 hit
        payload = {
            "requests": [
                {
                    "indexName": "m2live_default_products",
                    "query": mpn,
                    "params": "hitsPerPage=1&clickAnalytics=true&enablePersonalization=true"
                }
            ]
        }

        try:
            # Use AsyncSession from curl_cffi for non-blocking requests
            # impersonate="chrome124" mimics a modern Chrome browser TLS fingerprint
            async with AsyncSession() as s:
                response = await s.post(
                    url,
                    json=payload,
                    headers=headers,
                    impersonate="chrome124",
                    timeout=15
                )

                if response.status_code != 200:
                    logger.warning(f"JW API returned status {response.status_code}")
                    return self.not_found

                data = response.json()

                # Parse Algolia response structure
                # Structure: {'results': [{'hits': [{product_data}, ...]}]}
                results = data.get("results", [])
                if not results:
                    return self.not_found

                hits = results[0].get("hits", [])
                if not hits:
                    logger.warning(f"No hits found for MPN={mpn} via API")
                    return self.not_found

                product = hits[0]
                product_mpn = product.get('mpn', "")

                if not product_mpn or product_mpn != mpn:
                    logger.warning(
                        "Product not found for MPN=%s on JW Computers page",
                        mpn
                    )
                    return self.not_found

                # Extract Price
                # The API usually returns price in a 'price' field, which can be a dict or a float
                raw_price = product.get("price")
                final_price = None

                if isinstance(raw_price, dict):
                    # Try to extract AUD default price if it's a nested dictionary
                    final_price = raw_price.get("AUD", {}).get("default") or raw_price.get("default")
                else:
                    final_price = raw_price

                if not final_price:
                    logger.warning(f"Price field missing in API response for {mpn}")
                    return self.not_found

                # Extract URL
                # The API returns a relative path (e.g., "product-name.html")
                product_url = product.get("url")
                if product_url and not product_url.startswith("http"):
                    product_url = f"https://www.jw.com.au/{product_url}"

                return PriceResult(
                    vendor_id=self.vendor_id,
                    mpn=mpn,
                    price=float(final_price),
                    currency=self.currency,
                    url=product_url,
                    found=True
                )

        except Exception as e:
            logger.error(f"Error scraping JW via API: {e}")
            return self.not_found
