"""
PC Case Gear HTTP API Scraper.

This module implements a web scraper for PC Case Gear using their Algolia search API.
Provides fast, reliable scraping without browser automation.

Classes:
    PCCaseGearScraper: API-based scraper for www.pccasegear.com
"""

import logging
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class PCCaseGearScraper(BaseScraper):
    """
    Web scraper for PC Case Gear (www.pccasegear.com) using Algolia API.

    Queries PCCG's Algolia search backend for product information, avoiding
    the need for browser automation and JavaScript rendering.

    Attributes:
        vendor_id: Identifier "pc_case_gear"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = PCCaseGearScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> if result.found:
        ...     print(f"Price: ${result.price}")
    """

    vendor_id: str = "pc_case_gear"
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

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with complete product data if found, otherwise not_found result.
        """
        # PC Case Gear uses the Algolia search engine API
        url = "https://hpd3dbj2io-dsn.algolia.net/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(3.35.1)%3B%20Browser%20(lite)&x-algolia-application-id=HPD3DBJ2IO&x-algolia-api-key=9559cf1a6c7521a30ba0832ec6c38499"

        # Algolia API keys (public keys extracted from the website network traffic)
        headers = {
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Connection": "keep-alive",
            "Host": "hpd3dbj2io-dsn.algolia.net",
            "Origin": "https://www.pccasegear.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        # Construct the query payload
        payload = {
            "requests": [
                {
                    "indexName": "pccg_products",
                    "query": mpn,
                    "params": "hitsPerPage=1&clickAnalytics=true&enablePersonalization=true"
                }
            ]
        }

        try:
            # Use AsyncSession from curl_cffi for non-blocking requests
            async with AsyncSession() as s:
                response = await s.post(
                    url,
                    json=payload,
                    headers=headers,
                    impersonate="chrome124",
                    timeout=15
                )

                if response.status_code != 200:
                    logger.warning(f"PCCG API returned status {response.status_code}")
                    return self.not_found

                data = response.json()

                # Parse Algolia response structure
                results = data.get("results", [])
                if not results:
                    return self.not_found

                hits = results[0].get("hits", [])
                if not hits:
                    logger.warning(f"No hits found for MPN={mpn} via API")
                    return self.not_found

                product = hits[0]
                product_mpn = product.get('products_model', "")

                if not product_mpn or product_mpn != mpn:
                    logger.warning(
                        "Product not found for MPN=%s on PC Case Gear page",
                        mpn
                    )
                    return self.not_found

                # Extract Price
                price = product.get("products_price")
                if not price:
                    logger.warning(f"Price field missing in API response for {mpn}")
                    return self.not_found

                # Extract URL
                product_url = product.get("Product_URL")
                if product_url and not product_url.startswith("http"):
                    product_url = f"https://www.pccasegear.com{product_url}"

                return PriceResult(
                    vendor_id=self.vendor_id,
                    mpn=mpn,
                    price=float(price),
                    currency=self.currency,
                    url=product_url,
                    found=True
                )

        except Exception as e:
            logger.error(f"Error scraping PCCG via API: {e}")
            return self.not_found
