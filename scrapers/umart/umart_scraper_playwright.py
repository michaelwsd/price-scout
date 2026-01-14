"""
Backup Scraper for Umart
"""
import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

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
        url = f"https://www.umart.com.au/search.php?cat_id=&keywords={mpn}"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info("Scraping Umart for MPN=%s", mpn)

            try:
                await page.goto(
                    url,
                    wait_until="networkidle",  # wait for JS requests
                    timeout=60000              # 60 seconds
                )
            except Exception as e:
                logger.warning("Page failed to load for MPN=%s at %s: %s", mpn, url, e)
                return self.not_found

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')

            product_lst = soup.select_one("ul.list-unstyled.info.goods_row")
            if not product_lst:
                logger.warning(
                    "Product not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return self.not_found
            
            # get the first item
            product = product_lst.select_one("li.goods_info.search_goods_list")
            if not product:
                logger.warning(
                    "Product not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return self.not_found

            # get price from link
            link = "https://www.umart.com.au/" + product.select_one("a")["href"]

            try:
                await page.goto(
                    link,
                    wait_until="networkidle",  # wait for JS requests
                    timeout=60000              # 60 seconds
                )
            except Exception as e:
                logger.warning("Page failed to load for MPN=%s at %s: %s", mpn, url, e)
                return self.not_found

            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')
        
            mpn_div = soup.select_one("div.spec-right[itemprop='mpn']")
            if not mpn_div or mpn_div.get_text(strip=True) != mpn:
                logger.warning(
                    "Product not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return self.not_found

            price_text = soup.select_one("span.goods-price.ele-goods-price")
            if not price_text:
                logger.warning(
                    "Price not found for MPN=%s on Umart page %s",
                    mpn,
                    url,
                )
                return self.not_found
            else:
                price_text = price_text.get_text(strip=True)

            # Extract stock status
            in_stock = self._extract_stock_status(soup)

            await browser.close()

        return PriceResult(
            vendor_id=self.vendor_id,
            url=link,
            mpn=mpn,
            price=float(price_text),
            currency=self.currency,
            in_stock=in_stock,
            found=True
        )

    def _extract_stock_status(self, soup: BeautifulSoup) -> bool:
        """
        Extract stock availability status from the product page.

        Umart stock statuses:
        - "In Stock" = in stock
        - "Pre Order", "At Other Stores" = available but not immediate
        - "Out of Stock", "Discontinued" = not available

        Args:
            soup: BeautifulSoup object of the product page.

        Returns:
            True if in stock, False otherwise.
        """
        # Try multiple possible selectors for stock status
        stock_selectors = [
            "div.goods_stock",
            "span.stock-status",
            "div.stock-status",
            "div.availability",
            "span.availability",
            "div.product-stock",
            "div.goods-stock-info",
        ]

        for selector in stock_selectors:
            stock_elem = soup.select_one(selector)
            if stock_elem:
                stock_text = stock_elem.get_text(strip=True).lower()
                logger.debug("Umart stock text: %s", stock_text)

                # Check for in-stock indicators
                if "in stock" in stock_text:
                    return True
                # Check for out-of-stock indicators
                if "out of stock" in stock_text or "discontinued" in stock_text:
                    return False
                # "Pre Order", "At Other Stores" = not immediately in stock
                if "pre order" in stock_text or "preorder" in stock_text:
                    return False
                if "other store" in stock_text:
                    return True  # Available at other stores = still available

        # Check for "Add to Cart" button as fallback
        add_to_cart = soup.select_one("button.add-to-cart, a.add-to-cart, button.btn-addcart, a.btn-addcart")
        if add_to_cart:
            if add_to_cart.get("disabled") or "disabled" in add_to_cart.get("class", []):
                return False
            return True

        # Default to True if product exists with price
        return True