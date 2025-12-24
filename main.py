import time
import logging
import asyncio
import argparse

from scrapers.scorptec_scraper import ScorptecScraper
from scrapers.mwave_scraper import MwaveScraper
from scrapers.pc_case_gear_scraper import PCCaseGearScraper
from scrapers.jw_computer_scraper import JWComputersScraper
from scrapers.umart_scraper import UmartScraper
from scraper import read_mpns_from_csv, batch_scrape_mpns, write_results_to_csv

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

    parser = argparse.ArgumentParser(
        description="Computer Parts Price Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python main.py --mpn BX8071512100F
        python main.py --csv input.csv --output results.csv
        """
    )

    # Make --mpn and --csv mutually exclusive
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mpn", help="Manufacturer Part Number")
    group.add_argument("--csv", help="Path to CSV file containing MPNs (must have 'mpn' or 'name' column)")

    parser.add_argument("--output", help="Output CSV file path (only used with --csv)")

    args = parser.parse_args()

    # Initialize scrapers (reused for both single and batch modes)
    scrapers = [
        ("Scorptec", ScorptecScraper()),
        ("Mwave", MwaveScraper()),
        ("PC Case Gear", PCCaseGearScraper()),
        ("JW Computers", JWComputersScraper()),
        ("Umart", UmartScraper()),
    ]

    if args.mpn:
        # Single MPN query logic
        mpn = args.mpn.strip()
        logger.info("Starting price scout for MPN=%s", mpn)

        tasks = [scraper.scrape(mpn) for _, scraper in scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (vendor, _), result in zip(scrapers, results):
            if isinstance(result, Exception):
                logger.error("%s scraper failed: %s", vendor, result)
            elif result:
                logger.info("%s result: %s", vendor, result)
            else:
                logger.warning("No %s result found", vendor)

        elapsed = time.perf_counter() - start
        logger.info("All scrapers completed in %.2f seconds", elapsed)
        return results

    elif args.csv:
        # CSV batch processing
        csv_path = args.csv
        output_path = args.output or 'results.csv'

        logger.info("Reading MPNs from %s", csv_path)
        mpns = read_mpns_from_csv(csv_path)
        logger.info("Found %d MPNs to process", len(mpns))

        # Batch scrape
        batch_results = await batch_scrape_mpns(mpns, scrapers)

        # Write to CSV
        write_results_to_csv(batch_results, output_path)

        elapsed = time.perf_counter() - start
        logger.info("Batch processing completed in %.2f seconds", elapsed)

        return batch_results


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    results = asyncio.run(main())

    # Print results based on mode
    if isinstance(results, list):
        # Check if it's batch results (list of tuples) or single results (list of scraper results)
        if results and isinstance(results[0], tuple):
            # Batch mode - print summary
            print("\n" + "=" * 70)
            print("CSV BATCH PROCESSING SUMMARY")
            print("=" * 70)

            successful = sum(1 for _, result_dict in results if any(result_dict.values()))
            total = len(results)

            print(f"Total MPNs processed: {total}")
            print(f"Successfully found:   {successful}")
            print(f"Not found:           {total - successful}")
            print(f"Success rate:        {successful / total * 100:.1f}%")
            print("=" * 70)
            print("(Detailed results saved to CSV file)")
            print("=" * 70 + "\n")
        else:
            # Single MPN mode - original output
            for r in results:
                print(r)
                print()
    elif results:
        # Fallback for any other return type
        print(results)