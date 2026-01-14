"""
eBay Australia Playwright Scraper.

This module implements a web scraper for eBay Australia using Playwright
for browser automation. Extracts price, stock status, and item condition.

Classes:
    EbayScraper: Playwright-based scraper for www.ebay.com.au
"""

import logging
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class EbayScraper(BaseScraper):
    """
    Web scraper for eBay Australia using Playwright browser automation.

    Extracts price, stock availability, and item condition from product pages.

    Attributes:
        vendor_id: Identifier "ebay_au"
        currency: "AUD" (Australian Dollar)
        not_found: Default PriceResult for products not found

    Example:
        >>> scraper = EbayScraper()
        >>> result = await scraper.scrape("BX8071512100F")
        >>> print(f"Price: ${result.price}, Condition: {result.condition}")
    """

    vendor_id: str = "ebay_au"
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
        Scrape price data using Playwright browser automation.

        Args:
            mpn: Manufacturer Part Number to search for.

        Returns:
            PriceResult with complete product data if found, otherwise not_found result.
        """
        # Search URL for eBay Australia
        # LH_BIN=1: Buy It Now only
        # _sop=15: Sort by Price + Shipping: lowest first
        search_url = f"https://www.ebay.com.au/sch/i.html?_nkw={mpn}&LH_BIN=1&_sop=15"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info("eBay AU (Playwright): Searching for MPN=%s", mpn)

            try:
                await page.goto(
                    search_url,
                    wait_until="networkidle",
                    timeout=120000
                )
            except Exception as e:
                logger.warning("eBay AU (Playwright): Search page failed to load: %s", e)
                await browser.close()
                return self.not_found

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            # Find all search result items (try both layouts)
            items = soup.select("li.s-card")
            if not items:
                items = soup.select("li.s-item")

            if not items:
                logger.warning("eBay AU (Playwright): No search results found for MPN=%s", mpn)
                await browser.close()
                return self.not_found

            # Iterate through items
            for item in items[1:]:  # Skip first item (often placeholder)
                # Validate MPN in title
                title_elem = item.select_one("div.s-card__title span") or item.select_one("div.s-item__title")
                if not title_elem:
                    continue

                title_text = title_elem.get_text(strip=True)
                if mpn.lower() not in title_text.lower():
                    continue

                # Extract URL
                link_elem = item.select_one("a.s-card__link") or item.select_one("a.s-item__link")
                if not link_elem:
                    continue
                product_url = link_elem.get("href")
                if not product_url or "ebay.com.au/itm/" not in product_url:
                    continue

                # Visit product page to get detailed info (condition, stock)
                result = await self._scrape_product_page(page, product_url, mpn)
                if result.found:
                    await browser.close()
                    return result

            logger.warning("eBay AU (Playwright): No matching product found for MPN=%s", mpn)
            await browser.close()
            return self.not_found

    async def _scrape_product_page(self, page, product_url: str, mpn: str) -> PriceResult:
        """
        Scrape the product page to extract price, condition, and stock status.

        Args:
            page: Playwright page object.
            product_url: URL of the product page.
            mpn: Manufacturer Part Number.

        Returns:
            PriceResult with full product data.
        """
        try:
            await page.goto(
                product_url,
                wait_until="networkidle",
                timeout=60000
            )
        except Exception as e:
            logger.warning("eBay AU (Playwright): Product page failed to load: %s", e)
            return self.not_found

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")

        # Validate MPN in Item Specifics
        if not self._validate_mpn(soup, mpn):
            return self.not_found

        # Extract price
        price = self._extract_price(soup)
        if price is None:
            logger.warning("eBay AU (Playwright): Price not found for MPN=%s", mpn)
            return self.not_found

        # Extract condition
        condition = self._extract_condition(soup)

        # Extract stock status
        in_stock = self._extract_stock_status(soup)

        logger.info(
            "eBay AU (Playwright): Found MPN=%s, price=%.2f, condition=%s, in_stock=%s",
            mpn, price, condition, in_stock
        )

        return PriceResult(
            vendor_id=self.vendor_id,
            url=product_url,
            mpn=mpn,
            price=price,
            currency=self.currency,
            in_stock=in_stock,
            condition=condition,
            found=True
        )

    def _validate_mpn(self, soup: BeautifulSoup, mpn: str) -> bool:
        """
        Validate that the MPN on the product page matches.

        Args:
            soup: BeautifulSoup object of the product page.
            mpn: Manufacturer Part Number to validate.

        Returns:
            True if MPN matches, False otherwise.
        """
        # Method 1: Look for Item Specifics with ux-labels-values structure
        specifics_rows = soup.select("div.ux-labels-values")
        for row in specifics_rows:
            label = row.select_one("div.ux-labels-values__labels")
            value = row.select_one("div.ux-labels-values__values")

            if label and value:
                label_text = label.get_text(strip=True).lower()
                if "mpn" in label_text or "part number" in label_text:
                    value_text = value.get_text(strip=True)
                    if mpn.lower() == value_text.lower():
                        return True

        # Method 2: Search in the about-this-item section
        about_section = soup.select_one("div.x-about-this-item")
        if about_section:
            text = about_section.get_text()
            mpn_match = re.search(r'MPN[:\s]+([A-Za-z0-9\-]+)', text, re.IGNORECASE)
            if mpn_match and mpn_match.group(1).lower() == mpn.lower():
                return True

        # Method 3: Check title
        title_elem = soup.select_one("h1.x-item-title__mainTitle")
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if mpn.lower() in title_text.lower():
                return True

        logger.debug("eBay AU (Playwright): MPN=%s not found in product page", mpn)
        return False

    def _extract_price(self, soup: BeautifulSoup) -> float | None:
        """
        Extract price from the product page.

        Args:
            soup: BeautifulSoup object of the product page.

        Returns:
            Price as float, or None if not found.
        """
        price_selectors = [
            "div.x-price-primary span.ux-textspans",
            "div.x-bin-price span.ux-textspans",
            "span[itemprop='price']",
            "div.x-price-approx span.ux-textspans",
        ]

        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price is not None:
                    return price

        return None

    def _extract_condition(self, soup: BeautifulSoup) -> str:
        """
        Extract item condition from the product page.

        Args:
            soup: BeautifulSoup object of the product page.

        Returns:
            Condition string (e.g., "New", "Used", "Refurbished"), defaults to "New".
        """
        # Method 1: Look for condition in Item Specifics (ux-labels-values structure)
        specifics_rows = soup.select("div.ux-labels-values")
        for row in specifics_rows:
            label = row.select_one("div.ux-labels-values__labels")
            value = row.select_one("div.ux-labels-values__values")

            if label and value:
                label_text = label.get_text(strip=True).lower()
                if "condition" in label_text:
                    value_text = value.get_text(strip=True)
                    # Clean up: remove "Condition:" prefix if present
                    value_text = re.sub(r'^condition[:\s]*', '', value_text, flags=re.IGNORECASE).strip()
                    if value_text:
                        return value_text

        # Method 2: Look for condition with BOLD span (actual value, not label)
        condition_value_selectors = [
            "div.x-item-condition span.ux-textspans--BOLD",
            "div.x-item-condition span.ux-textspans--SECONDARY",
            "span.ux-condition-text",
        ]

        for selector in condition_value_selectors:
            condition_elem = soup.select_one(selector)
            if condition_elem:
                condition_text = condition_elem.get_text(strip=True)
                # Skip if it's just the label
                if condition_text and condition_text.lower() not in ["condition", "condition:"]:
                    return condition_text

        # Method 3: Get all spans in x-item-condition, skip the label
        condition_container = soup.select_one("div.x-item-condition")
        if condition_container:
            spans = condition_container.select("span.ux-textspans")
            for span in spans:
                text = span.get_text(strip=True)
                # Skip label spans, get the actual condition value
                if text and text.lower() not in ["condition", "condition:"]:
                    return text

        # Method 4: Search in about-this-item section with regex
        about_section = soup.select_one("div.x-about-this-item")
        if about_section:
            text = about_section.get_text()
            condition_match = re.search(
                r'Condition[:\s]+(New|Used|Refurbished|Open Box|For parts|Certified[^,]*)',
                text, re.IGNORECASE
            )
            if condition_match:
                return condition_match.group(1).strip()

        return "New"  # Default to New

    def _extract_stock_status(self, soup: BeautifulSoup) -> bool:
        """
        Extract stock availability status from the product page.

        Args:
            soup: BeautifulSoup object of the product page.

        Returns:
            True if in stock, False if out of stock.
        """
        # Method 1: Check for "Out of stock" or "Sold" indicators
        out_of_stock_indicators = [
            "div.d-quantity__availability",
            "span.d-quantity__availability",
            "div.x-quantity__availability",
        ]

        for selector in out_of_stock_indicators:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True).lower()
                if "out of stock" in text or "sold" in text or "not available" in text:
                    return False
                if "available" in text or "in stock" in text or "last one" in text:
                    return True
                # Check for quantity pattern like "3 available" or "More than 10 available"
                qty_match = re.search(r'(\d+)\s*available', text)
                if qty_match:
                    return int(qty_match.group(1)) > 0

        # Method 2: Look for quantity selector (if present, usually in stock)
        qty_input = soup.select_one("input#qtyTextBox") or soup.select_one("select#qtyDropdown")
        if qty_input:
            return True

        # Method 3: Check if "Add to cart" or "Buy It Now" button is present and enabled
        buy_buttons = soup.select("a.ux-call-to-action, button.ux-call-to-action")
        for btn in buy_buttons:
            btn_text = btn.get_text(strip=True).lower()
            if "buy it now" in btn_text or "add to cart" in btn_text:
                # Check if disabled
                if "disabled" not in btn.get("class", []) and not btn.get("disabled"):
                    return True

        # Method 4: Check for "ended" or "sold" in listing status
        listing_status = soup.select_one("div.vi-status-bar-wrapper, span.ux-timer")
        if listing_status:
            text = listing_status.get_text(strip=True).lower()
            if "ended" in text or "sold" in text:
                return False

        # Default: assume in stock for Buy It Now listings
        return True

    def _parse_price(self, price_text: str) -> float | None:
        """
        Parse price string to float.

        Args:
            price_text: Raw price text (e.g., "AU $245.00", "$245.00").

        Returns:
            Price as float, or None if parsing fails.
        """
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(",", ""))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass
        return None
