import time
import logging
import asyncio
import argparse

from scrapers.scorptec_scraper import ScorptecScraper
from scrapers.mwave_scraper import MwaveScraper
from scrapers.pc_case_gear_scraper import PCCaseGearScraper
from scrapers.jw_computer_scraper import JWComputersScraper
from scrapers.umart_scraper import UmartScraper

# -----------------------------------------------------------------------------
# Logging configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("price-scout")

# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
async def main():
    """Main entry point with argument parsing and routing."""
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Computer Parts Price Comparison Tool")
    parser.add_argument("--mpn", required=True)
    args = parser.parse_args()
    mpn = args.mpn.strip()

    logger.info("Starting price scout for MPN=%s", mpn)

    scrapers = [
        ("Scorptec", ScorptecScraper()),
        ("Mwave", MwaveScraper()),
        ("PC Case Gear", PCCaseGearScraper()),
        ("JW Computers", JWComputersScraper()),
        ("Umart", UmartScraper()),
    ]

    tasks = [scraper.scrape(mpn) for _, scraper in scrapers] # coroutine objects
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for (vendor, _), result in zip(scrapers, results):
        if isinstance(result, Exception):
            logger.error("%s scraper failed: %s", vendor, result)
        elif result:
            logger.info("%s result: %s", vendor, result)
        else:
            logger.warning("No %s result found", vendor)
    
    # log time
    elapsed = time.perf_counter() - start
    logger.info("All scrapers completed in %.2f seconds", elapsed)

    return results

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    results = asyncio.run(main())
    
    for r in results:
        print(r)
        print()
