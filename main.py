import time
import logging
import asyncio
import argparse
import csv
from typing import List
from decimal import Decimal

# Database imports
from database import init_db, save_result

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
# Helper functions for CSV batch processing
# -----------------------------------------------------------------------------
def read_mpns_from_csv(csv_path: str) -> List[str]:
    """Read MPNs from CSV file. Supports 'mpn' or 'name' column."""
    mpns = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        mpn_column = None
        if 'mpn' in reader.fieldnames:
            mpn_column = 'mpn'
        elif 'name' in reader.fieldnames:
            mpn_column = 'name'
        else:
            raise ValueError("CSV file must contain 'mpn' or 'name' column")

        for row in reader:
            if row.get(mpn_column, '').strip():
                mpns.append(row[mpn_column].strip())
    return mpns


async def scrape_single_mpn_async(mpn: str, scrapers):
    """Scrape a single MPN from all scrapers (async)."""
    tasks = [scraper.scrape(mpn) for _, scraper in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    result_dict = {}
    for (vendor, _), result in zip(scrapers, results):
        if isinstance(result, Exception):
            logger.error("%s scraper failed for %s: %s", vendor, mpn, result)
            result_dict[vendor] = None
        elif result:
            logger.info("%s result for %s: %s", vendor, mpn, result)
            result_dict[vendor] = result
        else:
            logger.warning("No %s result found for %s", vendor, mpn)
            result_dict[vendor] = None

    return mpn, result_dict


async def batch_scrape_mpns(mpns: List[str], scrapers):
    """Batch scrape multiple MPNs concurrently with a semaphore limit."""

    # Limit concurrency to 5 MPNs at a time
    semaphore = asyncio.Semaphore(5)

    async def bounded_scrape(index, mpn):
        async with semaphore:
            logger.info("Processing %d/%d: %s", index, len(mpns), mpn)
            return await scrape_single_mpn_async(mpn, scrapers)

    tasks = [bounded_scrape(i, mpn) for i, mpn in enumerate(mpns, 1)]

    # Run all tasks concurrently
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out any top-level exceptions in the batch process itself
    valid_results = []
    for res in all_results:
        if isinstance(res, Exception):
            logger.error("Batch task failed: %s", res)
        else:
            valid_results.append(res)

    return valid_results


def write_results_to_csv(results, output_path: str):
    """Write batch scraping results to CSV file."""
    if not results:
        logger.warning("No results to write")
        return

    fieldnames = ['mpn', 'lowest_price', 'lowest_price_vendor', 'lowest_price_url',
                  'scorptec_price', 'scorptec_url', 'mwave_price', 'mwave_url',
                  'pccasegear_price', 'pccasegear_url', 'jwcomputers_price', 'jwcomputers_url',
                  'umart_price', 'umart_url']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for mpn, result_dict in results:
            row = {'mpn': mpn}

            # Find lowest price
            lowest_price = None
            lowest_vendor = None
            lowest_url = None

            vendor_map = {
                'Scorptec': 'scorptec',
                'Mwave': 'mwave',
                'PC Case Gear': 'pccasegear',
                'JW Computers': 'jwcomputers',
                'Umart': 'umart'
            }

            for vendor_name, data in result_dict.items():
                vendor_key = vendor_map.get(vendor_name, vendor_name.lower())
                if data and data.price is not None:
                    if lowest_price is None or data.price < lowest_price:
                        lowest_price = data.price
                        lowest_vendor = vendor_key
                        lowest_url = str(data.url)
                    row[f'{vendor_key}_price'] = float(data.price)
                    row[f'{vendor_key}_url'] = str(data.url)
                else:
                    row[f'{vendor_key}_price'] = None
                    row[f'{vendor_key}_url'] = None

            row['lowest_price'] = float(lowest_price) if lowest_price else None
            row['lowest_price_vendor'] = lowest_vendor
            row['lowest_price_url'] = lowest_url

            writer.writerow(row)

    logger.info("Results written to %s", output_path)


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------
async def main():
    """Main entry point with argument parsing and routing."""

    # Initialize Database
    init_db()

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
                # Save to DB
                save_result(result)
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

        # Save batch results to DB
        logger.info("Saving batch results to database...")
        for mpn, result_dict in batch_results:
            for vendor_name, result_obj in result_dict.items():
                if result_obj:
                    save_result(result_obj)

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