"""
Center Com HTTP API Scraper.

Classes:
    CenterComScraper: API-based scraper for www.centercom.com.au
"""

import logging
import cloudscraper
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class CenterComScraper(BaseScraper):
    vendor_id: str = "centercom"
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
        Scrape price data using API and product page validation.

        Performs a two-step validation:
        1. Search via endpoint
        2. Verify exact MPN on product page

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with complete product data if found, otherwise not_found result.
        """
        search_url = f"https://computerparts.centrecom.com.au/api/search?cid=0ae1fd6a074947699fbe46df65ee5714&q={mpn}&ps=30"
        base_url = "https://www.centrecom.com.au/"

        logger.info("Scraping Center Com for MPN=%s", mpn)

        headers = {
                    "accept": "application/json, text/plain, */*",
                    "accept-encoding": "gzip, deflate, br, zstd",
                    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                    "origin": "https://www.centrecom.com.au",
                    "priority": "u=1, i",
                    "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
                }
        
        try:
            async with AsyncSession() as s:
                # 1. Get search results
                resp = await s.get(search_url, headers=headers, impersonate="chrome124")
                if resp.status_code != 200:
                    return self.not_found

                data = resp.json()

                if len(data['p']) == 0:
                    logger.warning(f"MPN not found on Center Com page for {mpn}.")
                    return self.not_found
                
                product = data['p'][0]
                in_stock = product['stockAvailablity'] == "IN STOCK"
                price_text = product['price']
                product_url = base_url + product['seName']

                # validate mpn
                scraper = cloudscraper.create_scraper()
                try:
                    res = scraper.get(product_url, timeout=20)
                    res.raise_for_status()
                except Exception as e:
                    logger.error("HTTP error fetching %s: %s", product_url, e)
                    return self.not_found

                soup = BeautifulSoup(res.text, "lxml")
                mpn_div = soup.select_one("span.value[itemprop='sku']").get_text()

                if mpn_div != mpn:
                    logger.warning(f"MPN not found on Center Com page for {mpn}.")
                    return self.not_found

                return PriceResult(
                    vendor_id=self.vendor_id,
                    mpn=mpn,
                    price=float(price_text),
                    currency=self.currency,
                    url=product_url,
                    in_stock=in_stock,
                    found=True
                )

        except Exception as e:
            logger.error(f"Error scraping Centercom: {e}")
            return self.not_found