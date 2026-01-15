"""
Computer Alliance HTTP API Scraper.

Classes:
    ComputerAllianceScraper: API-based scraper for www.computeralliance.com.au
"""

import logging
import cloudscraper
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from models.models import PriceResult
from models.base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class ComputerAllianceScraper(BaseScraper):
    vendor_id: str = "computeralliance"
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
        search_url = f"https://www.computeralliance.com.au/ws/PartsWS.asmx/GetInventorySearch?q=%22{mpn}%22"
        base_url = "https://www.computeralliance.com.au/"

        logger.info("Scraping Computer Alliance for MPN=%s", mpn)

        headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
                'content-type': 'application/json',
                'cookie': '.ASPXANONYMOUS=XE14UdeSJoG5gJC89Vin_iuIH5xodYYDtqUOVDlUIEzm9LaOwleEzbGbknxoBIqOwqDLJEGCdoPznNsY75ytQ97h31pse-0zI0dz2q0Coc0Le03bhdPyJHn94Wu-FYzGbz1zvg2; _gcl_au=1.1.1939743663.1766116337; _ga=GA1.1.1891376986.1766116337; _fbp=fb.2.1766116337655.543391068633682417; InStockOnly=false; OrderBy=Default; ASP.NET_SessionId=kztdntdhzbl4cpofk02ecj4h; _uetsid=5673c6b0f1da11f08ec2591935881fc6; _uetvid=1ca07db0dc8e11f095c6ef73387da5f3; apt_pixel=eyJkZXZpY2VJZCI6ImQ4ZjgwYjU0LWY3ODQtNDc1MS1iMTMzLWUwOTQ5MThlZmU0ZCIsInVzZXJJZCI6IiIsImV2ZW50SWQiOjUsImxhc3RFdmVudFRpbWUiOjE3Njg0NTgzODU2NDd9; _ga_L7K1VQY4QC=GS2.1.s1768458050$o8$g1$t1768458391$j52$l0$h0$dftX0D6ZWrUAuwgZ7rKF5VGsZ-kzubzX7AQ; _ga_BPT7T5W766=GS2.1.s1768458051$o8$g1$t1768458391$j52$l0$h1546375784$dujiuUh8Of-HDeomgkpxq46V_oEhRxt98uA',
                'priority': 'u=1, i',
                'referer': 'https://www.computeralliance.com.au/?srsltid=AfmBOoo5OKYlz0elbavlga2MmCSb06mTS8FOzl9mFR3q0FotGpgjxHH1',
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

                if len(data['d']) == 0:
                    logger.warning(f"MPN not found on Computer Alliance page for {mpn}.")
                    return self.not_found
                
                product = data['d'][0]
                in_stock = "instock" in product['Stock'] 
                price_text = product['Retail']
                product_url = base_url + product['TitleURL']

                # validate mpn
                scraper = cloudscraper.create_scraper()
                try:
                    res = scraper.get(product_url, timeout=20)
                    res.raise_for_status()
                except Exception as e:
                    logger.error("HTTP error fetching %s: %s", product_url, e)
                    return self.not_found

                soup = BeautifulSoup(res.text, "lxml")
                mpn_div = soup.select_one("strong[id='MPN']").get_text().split()[-1]

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
            logger.error(f"Error scraping Computer Alliance: {e}")
            return self.not_found