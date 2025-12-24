import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from models.models import PriceResult
from models.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class UmartScraper(BaseScraper):
    vendor_id: str = "umart"
    currency: str = "AUD" 

    async def scrape(self, mpn: str) -> PriceResult:
        url = f"https://www.umart.com.au/search.php?cat_id=&keywords={mpn}"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info("Scraping Umart for MPN=%s", mpn)

            await page.goto(
                url,
                wait_until="networkidle" # wait for JS requests
                )

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            product_lst = soup.select_one("ul.list-unstyled.info.goods_row")
            if not product_lst:
                logger.warning(
                    "Product not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return None
            
            # get the first item
            product = product_lst.select_one("li.goods_info.search_goods_list")
            if not product:
                logger.warning(
                    "Product not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return None

            # get price from link
            link = "https://www.umart.com.au/" + product.select_one("a")["href"]

            await page.goto(link)
            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')
        
            mpn_div = soup.select_one("div.spec-right[itemprop='mpn']")
            if not mpn_div or mpn_div.get_text(strip=True) != mpn:
                logger.warning(
                    "Product not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return None

            price_text = soup.select_one("span.goods-price.ele-goods-price")
            if not price_text:
                logger.warning(
                    "Price not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return None
            else:
                price_text = price_text.get_text(strip=True)

            await browser.close()

        return PriceResult(
            vendor_id=self.vendor_id,
            url=link,
            mpn=mpn,
            price=price_text,
            currency=self.currency,
        )