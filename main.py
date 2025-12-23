import logging
import argparse

from scrapers.scorptec_scraper import ScorptecScraper

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

    try:
        result = scorptec_scraper.scrape(mpn)

        if result:
            logger.info("Scrape successful for %s", mpn)
            print(result)
        else:
            logger.warning("No result found for %s", mpn)

    except Exception:
        logger.exception("Scraping failed for MPN=%s", mpn)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
