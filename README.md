# Price Scout

**Price Scout** is a web scraping and price comparison tool for computer parts in Australia. Search for computer components by their Manufacturer Part Number (MPN) across nine major Australian PC retailers and compare prices to find the best deals.

## Features

### Core Functionality
- **Multi-Vendor Price Scraping**: Compare prices across 9 major Australian retailers:
  - Scorptec Computers
  - Mwave Australia
  - PC Case Gear
  - JW Computers
  - Umart
  - Digicor
  - Center Com
  - Computer Alliance
  - CPL

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

## Recent Updates

- **Expanded Vendor Support**: Added 4 new vendors (Digicor, Center Com, Computer Alliance, CPL) for comprehensive Australian market coverage
- **Dual Scraper Implementations**: HTTP-based scrapers alongside browser-based versions for improved performance
- **Fallback Logic**: Enhanced scrapers with robust fallback mechanisms (HTTP → Playwright/cloudscraper)
- **API-Based Scraping**: Direct API access for Algolia-powered sites (PC Case Gear, JW Computers)
- **Enhanced Documentation**: Comprehensive docstrings added across all modules
- **curl_cffi Integration**: Browser impersonation for reliable API access
- **Improved Reliability**: Better error handling and site variation support

## Technology Stack

- **Python 3.12+**: Core programming language
- **SQLite**: Local database for price history
- **Streamlit**: Interactive web dashboard
- **Playwright**: Browser automation for JavaScript-rendered sites
- **cloudscraper**: HTTP requests with Cloudflare bypass capability
- **curl_cffi**: Alternative HTTP client for enhanced reliability
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
├── requirements.txt            # Python dependencies
├── app.db                      # SQLite database (auto-created)
│
├── scrapers/                   # Vendor-specific scraper implementations
│   ├── scorptec/              # Scorptec scraper modules
│   │   ├── scorptec_scraper.py           # Main fallback orchestrator
│   │   ├── scorptec_scraper_http.py      # HTTP API implementation
│   │   └── scorptec_scraper_cloud.py     # Cloudscraper implementation
│   ├── mwave_scraper.py       # Mwave (cloudscraper)
│   ├── digicor_scraper.py     # Digicor (cloudscraper)
│   ├── centercom_scraper.py   # Center Com (curl_cffi + API)
│   ├── computeralliance_scraper.py  # Computer Alliance (curl_cffi + API)
│   ├── cpl_scraper.py         # CPL (curl_cffi + API)
│   ├── pccg/                  # PC Case Gear scraper modules
│   │   ├── pc_case_gear_scraper.py       # Main fallback orchestrator
│   │   ├── pc_case_gear_scraper_http.py  # Algolia API implementation
│   │   └── pc_case_gear_scraper_playwright.py  # Playwright implementation
│   ├── jwc/                   # JW Computers scraper modules
│   │   ├── jw_computer_scraper.py        # Main fallback orchestrator
│   │   ├── jw_computer_scraper_http.py   # Algolia API implementation
│   │   └── jw_computer_scraper_playwright.py   # Playwright implementation
│   └── umart/                 # Umart scraper modules
│       ├── umart_scraper.py              # Main fallback orchestrator
│       ├── umart_scraper_http.py         # AJAX API implementation
│       └── umart_scraper_playwright.py   # Playwright implementation
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
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (required for some scrapers):
   ```bash
   playwright install chromium
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
2. Nine scrapers execute concurrently using `asyncio.gather()`
3. Each scraper:
   - Searches the vendor's website using the MPN
   - Extracts product details and price
   - Validates MPN matches
   - Returns a `PriceResult` object
4. Results are processed and saved to the database
5. Results displayed to user with best price highlighted

### Scraper Types

Each vendor scraper uses optimized scraping strategies:

- **HTTP/API Implementations**: Fast, lightweight scraping using various techniques
  - **cloudscraper**: Handles Cloudflare protection (Scorptec, Mwave, Digicor)
  - **curl_cffi**: Browser impersonation for API access (Center Com, Computer Alliance, CPL)
  - **Algolia API**: Direct search API queries (PC Case Gear, JW Computers)
  - Best for: CLI batch processing and quick queries

- **Browser-Based Implementations**: Playwright headless browser for JavaScript-heavy sites
  - Used by: PC Case Gear, JW Computers, Umart (as fallbacks)
  - Best for: Sites with dynamic content loading

- **Fallback Logic**: Most vendors include fallback mechanisms:
  - HTTP/API scrapers try first (faster)
  - Playwright scrapers as fallback (more reliable for complex pages)
  - Scorptec: HTTP → cloudscraper fallback
  - PC Case Gear, JW Computers, Umart: HTTP → Playwright fallback

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
- **Dual Implementations**: Most vendors have both HTTP and browser-based implementations for flexibility
  - HTTP versions (suffix `_http.py`) used in CLI for better performance
  - Browser versions used in web dashboard for reliability with dynamic content
  - Fallback implementations handle edge cases and site variations

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
