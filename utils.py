import asyncio
import logging

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
    """Run all 5 vendor scrapers concurrently for a single MPN"""

    root_logger = logging.getLogger()
    old_level = root_logger.level
    root_logger.setLevel(logging.ERROR)

    try:
        tasks = [scraper.scrape(mpn.strip()) for _, scraper in scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    finally:
        root_logger.setLevel(old_level)


if __name__ == "__main__":
    res = asyncio.run(scrape_mpn_single("BX8071512400"))
    for r in res:
        print(r)
