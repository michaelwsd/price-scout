import cloudscraper
import asyncio
import logging
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from type.models import PriceResult
from type.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ComputerAllianceScraper(BaseScraper):
    vendor_id: str = "computer_alliance"
    currency: str = "AUD"

    async def scrape(self, mpn: str) -> PriceResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scrape_sync, mpn)

    def scrape_sync(self, mpn: str) -> PriceResult:
        scraper = cloudscraper.create_scraper()

        # Computer Alliance search URL pattern
        url = f"https://www.computeralliance.com.au/search?search={mpn}"

        logger.info("Scraping Computer Alliance for MPN=%s", mpn)

        try:
            res = scraper.get(url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            logger.error("HTTP error fetching %s: %s", url, e)
            return None

        soup = BeautifulSoup(res.text, "lxml")

        # 1) Try parse as product page first (search may redirect to a product page)
        direct = self._extract_from_product_page(soup, res.url, mpn)
        if direct:
            return direct

        # 2) Otherwise parse as search results page
        result = self._extract_from_search_results(soup, res.url, mpn)
        if result:
            return result

        logger.warning("Product not found for MPN=%s on Computer Alliance page %s", mpn, url)
        return None

    def _extract_from_product_page(self, soup: BeautifulSoup, page_url: str, mpn: str) -> PriceResult:
        # Detect product page by common detail-page labels
        full_text = soup.get_text(" ", strip=True)
        if "Manufacturer PN" not in full_text and "Product Code" not in full_text:
            return None

        # Verify MPN appears on the page (normalized match)
        if self._normalize(mpn) not in self._normalize(full_text):
            return None

        # Extract price from the main price element if possible, fallback to top-of-page text window
        price_node = soup.select_one("#ProductPrice, .product-price, .price")
        price_src = price_node.get_text(" ", strip=True) if price_node else full_text

        price = self._first_price(price_src)
        if not price:
            price = self._first_price(full_text[:1000])

        if not price:
            logger.warning("Price not found for MPN=%s on Computer Alliance product page %s", mpn, page_url)
            return None

        return PriceResult(
            vendor_id=self.vendor_id,
            url=page_url,
            mpn=mpn,
            price=price,
            currency=self.currency,
        )

    def _extract_from_search_results(self, soup: BeautifulSoup, page_url: str, mpn: str) -> PriceResult:
        norm_mpn = self._normalize(mpn)

        # Walk candidate product links and match MPN inside a nearby product container
        seen = set()

        # Prefer common search-result areas first; keep a generic fallback at the end
        anchors = soup.select(
            "div.fp_product_list a[href], div.search-results a[href], ul.ais-Hits-list a[href], a[href]"
        )

        for a in anchors:
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue
            if href in seen:
                continue
            seen.add(href)

            # Find a reasonable container around this link that likely holds product info
            container = a.find_parent("div", class_=re.compile(r"(product|item|col-)", re.I))
            if not container:
                continue

            container_text = container.get_text(" ", strip=True)

            # Match MPN within container text (normalized)
            if norm_mpn not in self._normalize(container_text):
                continue

            # Extract the first price inside this container
            price = self._first_price(container_text)
            if not price:
                continue

            product_url = urljoin(page_url, href)

            return PriceResult(
                vendor_id=self.vendor_id,
                url=product_url,
                mpn=mpn,
                price=price,
                currency=self.currency,
            )

        return None

    def _first_price(self, s: str) -> str | None:
        # Extract the first $xxx[.xx] occurrence and normalize it to plain numeric string
        m = re.search(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)", s)
        if not m:
            return None
        return m.group(1).replace(",", "").strip()

    def _normalize(self, s: str) -> str:
        # Normalize strings for robust MPN matching
        return re.sub(r"[^A-Z0-9]", "", (s or "").upper())
