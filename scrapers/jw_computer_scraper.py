import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from models.models import PriceResult
from models.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class JWComputersScraper(BaseScraper):
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
        url = f"https://www.jw.com.au/catalogsearch/result/?q={mpn}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info("Scraping JW Computers for MPN=%s", mpn)

            await page.goto(
                url,
                wait_until="networkidle" # wait for JS requests
                )

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            product_lst = soup.select_one("ol.ais-InfiniteHits-list")
            if not product_lst:
                logger.warning(
                    "Product not found for MPN=%s on JW Computers page %s",
                    mpn,
                    url,
                )
                return self.not_found
            
            # get the first item
            product = product_lst.select_one("li.ais-InfiniteHits-item")
            if not product:
                logger.warning(
                    "Product not found for MPN=%s on JW Computers page %s",
                    mpn,
                    url,
                )
                return self.not_found

            # get price from link
            link = product.select_one("a.result")["href"]

            await page.goto(link)
            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')
        
            mpn_div = soup.select_one("div.value[itemprop='mpn']")
            if not mpn_div or mpn_div.get_text(strip=True) != mpn:
                logger.warning(
                    "Product not found for MPN=%s on JW Computers page %s",
                    mpn,
                    url,
                )
                return self.not_found

            price_text = soup.select("span.price")[-1]
            if not price_text:
                logger.warning(
                    "Price not found for MPN=%s on JW Computers page %s",
                    mpn,
                    url,
                )
                return self.not_found
            else:
                price_text = price_text.get_text(strip=True).replace(",", "")[1:]

            await browser.close()

        return PriceResult(
            vendor_id=self.vendor_id,
            url=link,
            mpn=mpn,
            price=price_text,
            currency=self.currency,
            found=True
        )