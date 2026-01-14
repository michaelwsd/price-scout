import logging
import re
from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ScorptecScraper(BaseScraper):
    vendor_id: str = "scorptec"
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
        Scrapes product pricing information from Scorptec using their search API.

        This method queries Scorptec's search endpoint, extracts the HTML template
        from the JavaScript response, parses the product data, and validates the MPN
        before returning pricing information.

        Args:
            mpn: Manufacturer Part Number to search for

        Returns:
            PriceResult: An object containing:
                - vendor_id: "scorptec"
                - mpn: The manufacturer part number
                - price: Product price as a float (in AUD)
                - currency: "AUD"
                - url: Direct product URL (unquoted from tracker link)
                - found: True if product was found and matched, False otherwise

        Process:
            1. Queries Scorptec's search API with the provided MPN
            2. Extracts HTML template from JavaScript response using regex
            3. Parses HTML to find the first product result
            4. Validates that the found product's SKU matches the requested MPN (case-insensitive)
            5. Extracts and decodes the product URL from the tracker link
            6. Extracts the price from the product data

        Returns not_found PriceResult if:
            - HTTP request fails (non-200 status)
            - HTML template cannot be extracted from response
            - No product is found in the results
            - Product SKU doesn't match the requested MPN
            - Price information is missing
            - Any exception occurs during scraping
        """
        search_url = f"https://scorptec.resultspage.com/search?ts=rac-data&w={mpn}&rt=rac"

        headers = {
            "accept": "*/*",
            "referer": "https://www.scorptec.com.au/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }

        try:
            async with AsyncSession() as s:
                resp = await s.get(search_url, headers=headers, impersonate="chrome124")
                if resp.status_code != 200:
                    return self.not_found

                # 1. Extract the HTML template from the JS response
                template_match = re.search(r"template:\s*'(.*?)'\}", resp.text, re.DOTALL)
                if not template_match:
                    return self.not_found
                
                html_content = template_match.group(1).replace("\\'", "'").replace('\\"', '"')
                soup = BeautifulSoup(html_content, "html.parser")
                
                # 2. Get the first product
                first_product = soup.find("div", class_="sli_ac_product")
                if not first_product:
                    return self.not_found

                # 3. Validate MPN
                found_sku = first_product.get("data-sku", "").strip()
                if found_sku.lower() != mpn.lower():
                    return self.not_found
                
                # 4. Extract and Unquote the URL
                tracker_link = first_product.select_one("a[data-role='main-link']")['href']
                
                # Parse the tracker URL to find the 'url' parameter
                parsed_url = urlparse(tracker_link)
                params = parse_qs(parsed_url.query)
                
                if 'url' in params:
                    # unquote converts %3a to : and %2f to /
                    final_url = unquote(params['url'][0])
                else:
                    final_url = tracker_link

                # 5. Extract Price
                price_tag = first_product.select_one("div.price.sli_real_price")
                if not price_tag:
                    return self.not_found

                price_text = price_tag.get_text(strip=True)
                price = float(re.sub(r'[^\d.]', '', price_text))

                # 6. Extract stock status from search results (if available)
                in_stock = None  # Default unknown from search API
                stock_elem = first_product.select_one("div.stock, span.stock, div.availability")
                if stock_elem:
                    stock_text = stock_elem.get_text(strip=True).lower()
                    if "in stock" in stock_text or "available" in stock_text:
                        in_stock = True
                    elif "sold out" in stock_text or "out of stock" in stock_text:
                        in_stock = False

                return PriceResult(
                    vendor_id=self.vendor_id,
                    mpn=mpn,
                    price=price,
                    currency=self.currency,
                    url=final_url,
                    in_stock=in_stock,
                    found=True
                )

        except Exception as e:
            logger.error(f"Error scraping Scorptec: {e}")
            return self.not_found