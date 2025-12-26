# Price Scout

**Price Scout** is a web scraping and price comparison tool for computer parts in Australia. Search for computer components by their Manufacturer Part Number (MPN) across five major Australian PC retailers and compare prices to find the best deals.

## Features

### Core Functionality
- **Multi-Vendor Price Scraping**: Compare prices across 5 major Australian retailers:
  - Scorptec Computers
  - Mwave Australia
  - PC Case Gear
  - JW Computers
  - Umart

- **Dual Interface**:
  - Modern web dashboard built with Streamlit
  - Command-line interface for scripting and automation

- **Single MPN Query**: Search for individual products and get real-time price comparisons

- **Batch Processing**: Upload CSV files containing multiple MPNs and process them in bulk
  - Progress tracking with real-time updates
  - Success rate metrics and statistics
  - Processing time analysis
  - Automatic best price identification
  - Export results to CSV

- **Price History & Analytics**:
  - SQLite database stores all price data
  - Track price changes over time
  - Interactive price trend visualizations
  - Average price analysis by vendor
  - Price range statistics

### Technical Features
- **Asynchronous Scraping**: Uses `asyncio` for concurrent requests across all vendors
- **Multi-threading**: Processes multiple MPNs simultaneously with rate limiting
- **Cloudflare Bypass**: Handles Cloudflare-protected sites
- **JavaScript Rendering**: Uses Playwright for JavaScript-heavy sites
- **Smart Database Logic**:
  - Creates new record when price changes
  - Updates timestamp when price remains the same
  - Prevents duplicate data while maintaining complete history

## Technology Stack

- **Python 3.12+**: Core programming language
- **SQLite**: Local database for price history
- **Streamlit**: Interactive web dashboard
- **Playwright**: Browser automation for JavaScript-rendered sites
- **cloudscraper**: HTTP requests with Cloudflare bypass capability
- **BeautifulSoup4**: HTML parsing
- **Pandas**: Data manipulation and CSV handling
- **Plotly**: Interactive data visualizations
- **Pydantic**: Data validation and schema modeling

## Project Structure

```
price-scout/
├── app.py                      # Streamlit dashboard application
├── main.py                     # CLI entry point
├── scraper.py                  # Core scraping logic and batch processing
├── test.py                     # Manual testing script
├── app.db                      # SQLite database (auto-created)
│
├── scrapers/                   # Vendor-specific scraper implementations
│   ├── scorptec_scraper.py    # Scorptec (cloudscraper)
│   ├── mwave_scraper.py       # Mwave (cloudscraper)
│   ├── pc_case_gear_scraper.py # PC Case Gear (Playwright)
│   ├── jw_computer_scraper.py  # JW Computers (Playwright)
│   └── umart_scraper.py        # Umart (Playwright)
│
├── models/                     # Data models and base classes
│   ├── models.py              # PriceResult Pydantic model
│   └── base_scraper.py        # Abstract base scraper class
│
└── db/                         # Database layer
    └── db_manager.py          # DatabaseManager with all DB operations
```

## Installation

### Prerequisites
- Python 3.12 or higher
- Git

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd price-scout
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install streamlit pandas plotly playwright cloudscraper beautifulsoup4 lxml pydantic requests
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

   If you encounter permission issues or prefer a lighter installation:
   ```bash
   playwright install chromium --with-deps
   ```

## Usage

### Web Dashboard

Start the Streamlit web application:

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501` with three main tabs:

1. **Single Query**: Search for one product by MPN
2. **Batch Processing**: Upload a CSV file with multiple MPNs
3. **Analytics**: View price history and trends

### Command Line Interface (CLI)

**Single MPN Query**:
```bash
python main.py --mpn BX8071512400
```

**Batch Processing**:
```bash
python main.py --csv input.csv --output results.csv
```

### CSV Format for Batch Processing

Your CSV file must contain an `mpn` column:

```csv
mpn
BX8071512400
SNV3S/2000G
BX8071512100F
```

## How It Works

### Scraping Architecture

1. User inputs MPN via CLI or web dashboard
2. Five scrapers execute concurrently using `asyncio.gather()`
3. Each scraper:
   - Searches the vendor's website using the MPN
   - Extracts product details and price
   - Validates MPN matches
   - Returns a `PriceResult` object
4. Results are processed and saved to the database
5. Results displayed to user with best price highlighted

### Scraper Types

- **Static Sites** (Scorptec, Mwave): Use `cloudscraper` for fast HTTP requests with Cloudflare bypass
- **JavaScript Sites** (PC Case Gear, JW Computers, Umart): Use Playwright headless browser for JavaScript rendering

### Database Schema

The application uses SQLite with smart price tracking:
- Each product is identified by unique MPN
- Price history tracked with timestamps
- When scraping:
  - If price changed: Create new price record
  - If price unchanged: Update timestamp of latest record
- Supports queries for trends, averages, and historical analysis

## Development

### Testing Individual Scrapers

Use [test.py](test.py) to test individual scrapers:

```python
python test.py
```

Modify the script to test specific vendors or MPNs.

### Code Structure

- **Base Scraper**: All scrapers inherit from `BaseScraper` in [models/base_scraper.py](models/base_scraper.py)
- **Models**: Pydantic models in [models/models.py](models/models.py) ensure data validation
- **Database**: Centralized database operations in [db/db_manager.py](db/db_manager.py)
- **Scraper Logic**: Main scraping orchestration in [scraper.py](scraper.py)

## Limitations

- **Australian Market Only**: Scrapers are configured for Australian PC retailers
- **MPN Required**: Products must have valid manufacturer part numbers
- **Rate Limiting**: Batch processing includes delays to avoid overwhelming vendor servers
- **Headless Browser**: Some scrapers require Chromium (installed via Playwright)

## Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) for the web dashboard
- [Playwright](https://playwright.dev/python/) for browser automation
- [cloudscraper](https://github.com/venomous/cloudscraper) for Cloudflare bypass
- [Plotly](https://plotly.com/python/) for interactive visualizations
