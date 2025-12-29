import csv
import time
import logging
import asyncio
from typing import List

from scrapers.scorptec_scraper import ScorptecScraper
from scrapers.mwave_scraper import MwaveScraper
from scrapers.pccg.pc_case_gear_scraper_http import PCCaseGearScraper
from scrapers.jwc.jw_computer_scraper_http import JWComputersScraper
from scrapers.umart.umart_scraper_http import UmartScraper

# -----------------------------------------------------------------------------
# Logging configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("price-scout")

# -----------------------------------------------------------------------------
# Scrape all 5 vendors for a single MPN concurrently
# -----------------------------------------------------------------------------
async def scrape_mpn_single(mpn):
    start = time.perf_counter()
    mpn = mpn.strip()

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

    # Limit concurrency to 5 MPNs at a time to avoid rate limiting
    # (Since each MPN triggers 5 internal requests, this equals ~25 total concurrent connections)
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
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    results = asyncio.run(scrape_mpn_single())
    
    for r in results:
        print(r)
        print()
