import logging
import re
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class UmartScraper(BaseScraper):
    vendor_id: str = "umart"
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
        search_url = f"https://www.umart.com.au/ajax_search.php?act=tipword&word={mpn}______0"
        
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "referer": "https://www.umart.com.au/"
        }

        try:
            async with AsyncSession() as s:
                # 1. Get search results
                resp = await s.get(search_url, headers=headers, impersonate="chrome124")
                if resp.status_code != 200:
                    return self.not_found

                data = resp.json()
                html_fragment = data.get("search_product", "")
                if not html_fragment:
                    return self.not_found

                # 2. Extract the first product only
                soup = BeautifulSoup(html_fragment, "lxml")
                first_item = soup.find("li")
                if not first_item:
                    return self.not_found

                name_tag = first_item.find("div", class_="goods_name").find("a")
                product_url = name_tag["href"]
                price_text = first_item.find("div", class_="goods_price").get_text(strip=True)

                # 3. Visit product page to validate MPN exactly
                page_resp = await s.get(product_url, headers=headers, impersonate="chrome124")
                if page_resp.status_code == 200:
                    page_soup = BeautifulSoup(page_resp.text, "lxml")
                    mpn_div = page_soup.select_one("div.spec-right[itemprop='mpn']")
                    
                    if not mpn_div or mpn_div.get_text(strip=True) != mpn:
                        logger.warning(f"MPN not found on Umart page for {mpn}.")
                        return self.not_found

                    # 4. Clean price and return
                    price_text = page_soup.select_one("span.goods-price.ele-goods-price")
                    if not price_text:
                        logger.warning(
                            "Price not found for MPN=%s on Umart page",
                            mpn,
                        )
                        return self.not_found
                    else:
                        price_text = price_text.get_text(strip=True)

                    return PriceResult(
                        vendor_id=self.vendor_id,
                        mpn=mpn,
                        price=float(price_text),
                        currency=self.currency,
                        url=product_url,
                        found=True
                    )
                else:
                    logger.warning(
                        "Request error on Umart product page for MPN=%s",
                        mpn,
                    )
                    return self.not_found

        except Exception as e:
            logger.error(f"Error scraping Umart: {e}")
            return self.not_found