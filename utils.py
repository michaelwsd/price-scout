import asyncio

from scrapers.scorptec_scraper import ScorptecScraper
from scrapers.mwave_scraper import MwaveScraper
from scrapers.pc_case_gear_scraper import PCCaseGearScraper
from scrapers.jw_computer_scraper import JWComputersScraper
from scrapers.umart_scraper import UmartScraper

scrapers = [
                ("Scorptec", ScorptecScraper()),
                ("Mwave", MwaveScraper()),
                ("PC Case Gear", PCCaseGearScraper()),
                ("JW Computers", JWComputersScraper()),
                ("Umart", UmartScraper()),
            ]

async def scrape_mpn_single(mpn):
    """Scrape all 5 vendors for a single MPN concurrently"""

    mpn = mpn.strip()
    tasks = [scraper.scrape(mpn) for _, scraper in scrapers] # coroutine objects
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


if __name__ == "__main__":
    res = asyncio.run(scrape_mpn_single("ST8000VN002"))
    for r in res:
        print(r)
        print()
