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
def main():
    """Main entry point with argument parsing and routing."""

    parser = argparse.ArgumentParser(
        description="Computer Parts Price Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python main.py --mpn BX8071512100F
        """
        )

    parser.add_argument(
        "--mpn",
        required=True,
        help="Manufacturer Part Number (e.g. BX8071512100F)",
    )

    args = parser.parse_args()
    mpn = args.mpn.strip()

    logger.info("Starting price scout")
    logger.info("Searching for MPN=%s", mpn)

    scorptec_scraper = ScorptecScraper()
    mwave_scraper = MwaveScraper()
    pccg_scraper = PCCaseGearScraper()
    jwc_scraper = JWComputersScraper()
    umart_scraper = UmartScraper()

    try:
        scorptec_result = asyncio.run(scorptec_scraper.scrape(mpn))
        mwave_result = asyncio.run(mwave_scraper.scrape(mpn))
        pccg_result = asyncio.run(pccg_scraper.scrape(mpn))
        jwc_result = asyncio.run(jwc_scraper.scrape(mpn))
        umart_result = asyncio.run(umart_scraper.scrape(mpn))

        if scorptec_result: logger.info("Scorptec result for %s: %s", mpn, scorptec_result)
        else: logger.warning("No Scorptec result found for %s", mpn)

        if mwave_result: logger.info("Mwave result for %s: %s", mpn, mwave_result)
        else: logger.warning("No Mwave result found for %s", mpn)

        if pccg_result: logger.info("PC Case Gear result for %s: %s", mpn, pccg_result)
        else: logger.warning("No PC Case Gear result found for %s", mpn)

        if jwc_result: logger.info("JW Computers result for %s: %s", mpn, jwc_result)
        else: logger.warning("No JW Computers result found for %s", mpn)

        if umart_result: logger.info("Umart result for %s: %s", mpn, umart_result)
        else: logger.warning("No Umart result found for %s", mpn)

    except Exception:
        logger.exception("Scraping failed for MPN=%s", mpn)

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
