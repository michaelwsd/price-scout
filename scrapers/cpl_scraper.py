"""
CPL HTTP API Scraper.

Classes:
    CPLScraper: API-based scraper for www.cplonline.com.au
"""

import logging
import cloudscraper
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class CPLScraper(BaseScraper):
    vendor_id: str = "cpl"
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
        search_url = f"https://cplonline.com.au/search/ajax/suggest/?q={mpn}"

        logger.info("Scraping CPL for MPN=%s", mpn)

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'content-type': 'application/json',
            'cookie': '__zlcmid=1VEo9mawizRqW9m; form_key=mRctfUNX9Kwa7XJX; PHPSESSID=04ng06vg3h4r9mk9oo6ihkq060; mage-cache-sessid=true; section_data_ids={%22customer%22:1768459735%2C%22compare-products%22:1768459735%2C%22last-ordered-items%22:1768459735%2C%22cart%22:1768459735%2C%22directory-data%22:1768459735%2C%22captcha%22:1768459735%2C%22instant-purchase%22:1768459735%2C%22loggedAsCustomer%22:1768459735%2C%22persistent%22:1768459735%2C%22review%22:1768459735%2C%22wishlist%22:1768459735%2C%22recently_viewed_product%22:1768459735%2C%22recently_compared_product%22:1768459735%2C%22product_data_storage%22:1768459735}',
            'priority': 'u=1, i',
            'referer': 'https://cplonline.com.au/?srsltid=AfmBOorXtJCR0mF_riDMNjizbxBSpTNqNrojveIqKeMioW0q49PgtTzv',
            'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        try:
            async with AsyncSession() as s:
                # 1. Get search results
                resp = await s.get(search_url, headers=headers, impersonate="chrome124")
                if resp.status_code != 200:
                    return self.not_found

                data = resp.json()
                
                possible_urls = []

                # get the top 2 urls to prevent similar product error
                for item in data:
                    if item.get("type") == "product":
                        possible_urls.append(item['url'].replace(r"\/", "/"))
                        
                        if len(possible_urls) == 2:
                            break
                
                # validate mpn
                scraper = cloudscraper.create_scraper()
                    
                for url in possible_urls:
                    try:
                        res = scraper.get(url, timeout=20)
                        res.raise_for_status()
                    except Exception as e:
                        logger.error("HTTP error fetching %s: %s", url, e)
                        return self.not_found

                    soup = BeautifulSoup(res.text, "lxml")
                    mpn_div = soup.select_one("div.value[itemprop='mpn']").get_text()

                    if mpn_div != mpn:
                        continue 
                    
                    price_text = soup.select_one("span.price").get_text()[1:]
                    in_stock = soup.select_one("div.stock-item.in-stock").select_one("span").get_text() == "In Stock"

                    return PriceResult(
                        vendor_id=self.vendor_id,
                        mpn=mpn,
                        price=float(price_text),
                        currency=self.currency,
                        url=url,
                        in_stock=in_stock,
                        found=True
                    )

                logger.warning(f"MPN not found on CPL page for {mpn}.")
                return self.not_found

        except Exception as e:
            logger.error(f"Error scraping CPL: {e}")
            return self.not_found