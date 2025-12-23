import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from type.models import PriceResult
from type.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class PCCaseGearScraper(BaseScraper):
    vendor_id: str = "pccasegear"
    currency: str = "AUD" 

    async def scrape(self, mpn: str) -> PriceResult:
        url = f"https://www.pccasegear.com/search?query={mpn}"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info("Scraping PC Case Gear for MPN=%s", mpn)

            await page.goto(
                url,
                wait_until="networkidle" # wait for JS requests
                )

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            product_lst = soup.select_one("ul.ais-Hits-list")
            if not product_lst:
                logger.warning(
                    "Product not found for MPN=%s on PC Case Gear page %s",
                    mpn,
                    url,
                )
                return None
            
            # get the first item
            product = product_lst.select_one("li.ais-Hits-item")
            if not product:
                logger.warning(
                    "Product not found for MPN=%s on PC Case Gear page %s",
                    mpn,
                    url,
                )
                return None

            # get link 
            link = "https://www.pccasegear.com" + product.select_one("a.product-title")["href"]

            # get mpn
            mpn_div = product.select_one("span.product-model")
            if not mpn_div or mpn_div.get_text(strip=True) != mpn:
                logger.warning(
                    "Product not found for MPN=%s on PC Case Gear page %s",
                    mpn,
                    url,
                )
                return None

            # get price
            price_text = product.select_one("div.price")
            if not price_text:
                logger.warning(
                    "Price not found for MPN=%s on PC Case Gear page %s",
                    mpn,
                    url,
                )
                return None
            else:
                price_text = price_text.get_text(strip=True)[1:]

            await browser.close()

        return PriceResult(
            vendor_id=self.vendor_id,
            url=link,
            mpn=mpn,
            price=price_text,
            currency=self.currency,
        )