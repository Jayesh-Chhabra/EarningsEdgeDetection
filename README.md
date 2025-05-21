# EarningsEdgeDetection

A sophisticated scanner for identifying high-probability earnings trades based on volatility term structure and other key metrics.

## Features

* Multi-tier trade categorization system
* Strict filtering criteria for high-quality trade selection
* Automatically determines relevant earnings dates based on current time
* Scans both post-market and pre-market earnings announcements
* Multiple data sources (Investing.com, DoltHub, and Finnhub) for reliable earnings data
* Performance optimized scanning process
* Comprehensive metrics tracking
* Iron fly strategy recommendations with break-even analysis

## Trade Categories

The scanner organizes results into three categories:

1. **TIER 1 RECOMMENDED TRADES**
   - Meets all core filtering criteria
   - Term structure <= -0.004 (required for all categories)
   - Highest probability setups

2. **TIER 2 RECOMMENDED TRADES**
   - Near misses with term structure <= -0.006
   - Has exactly one near-miss criteria failure
   - Term structure <= -0.004 (required for all categories)

3. **NEAR MISSES**
   - Meets most criteria with minor issues
   - Term structure <= -0.004 (required for all categories)
   - Good candidates to watch

## Installation
 
1. Clone the repository:
```bash
git clone https://github.com/Jayesh-Chhabra/EarningsEdgeDetection.git
cd EarningsEdgeDetection/cli_scanner
```
 
2. Create and activate a virtual environment (not required, I personally don't but generally it is recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
 
3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Install additional dependencies:
```bash
pip install yahooquery webdriver-manager
```
 
5. Install Chrome WebDriver (required for Market Chameleon scraping):
   - The script will automatically download the appropriate ChromeDriver version
   - Ensure you have Google Chrome installed on your system
 
## Usage

Prerequisite:

Make sure (within the cli_scanner folder) you run ```chmod +x ./run.sh``` before proceeding so that you don't run into a permissions issue

Basic usage:
```bash
./run.sh [MM/DD/YYYY]
```

The run.sh script automatically detects the optimal number of worker threads for your system.

To run manually with custom settings:
```bash
python scanner.py --date "04/20/2025" --parallel 4
```

Optional parameters:
- `--date`, `-d`: Specific date to scan in MM/DD/YYYY format
- `--parallel`, `-p`: Number of worker threads (0 disables parallel processing)
- `--list`, `-l`: Show compact output with only ticker symbols and tiers
- `--iron-fly`, `-i`: Calculate and display recommended iron fly strikes
- `--use-dolthub`, `-u`: Use DoltHub and Finnhub as earnings data sources (see Data Source Integrations section)
- `--all-sources`, `-c`: Use all available earnings data sources combined

## Filtering Criteria

### Hard Filters (No Exceptions)
- Stock price >= $10.00
- Options expiration <= 9 days away
- Open interest >= 2000 contracts (combined calls/puts)
- Term structure <= -0.004 (for ALL categories, including near misses)
- ATM option deltas <= 0.57 in absolute value (ensures proper ATM selection)
- Expected move >= $0.90 (minimum dollar amount for nearest expiration)
- Options availability: Must have options chain
- Core analysis: Must complete successfully

### Additional Criteria
- Average daily volume >= 1.5M shares
- Winrate >= 50% (40-50% is near miss/Tier 2 eligible)
- IV/RV ratio >= 1.25 (preferred)

### Near Miss Ranges
1. Price
   - Pass: >= $10.00 (hard filter)
   - Fail: < $10.00

2. Volume (30-day average)
   - Pass: ≥ 1,500,000
   - Near Miss: 1,000,000 - 1,499,999
   - Fail: < 1,000,000

3. Winrate (previously Market Chameleon Overestimate)
   - Pass: >= 50%
   - Near Miss: 40-49.9%
   - Fail: < 40%

4. IV/RV Ratio
   - Pass: ≥ 1.25
   - Near Miss: 1.00 - 1.24
   - Fail: < 1.00

## Iron Fly Strategy

When using the `--iron-fly` or `-i` flag, the scanner will calculate recommended iron fly trades for each qualifying stock:

- Selects ATM options closest to 50 delta for short strikes
- Calculates wing widths based on 3x credit received
- Provides detailed analysis including:
  - Short and long strikes for puts and calls
  - Premium received and paid
  - Break-even price range
  - Risk-to-reward ratio
  - Maximum profit and maximum risk

## Output Explanation
 
For each stock, the following metrics are displayed:
* Current price
* 30-day average volume
* Expected move (in dollars)
* Winrate: Percentage and number of earnings periods analyzed
* IV/RV ratio
* Term structure (volatility curve slope)

With the `--iron-fly` flag, additional trade specifics are provided.

## Time-Based Logic
 
 If run before 4 PM Eastern:
  - Checks today's post-market earnings
  - Checks tomorrow's pre-market earnings
 
 If run after 4 PM Eastern:
  - Checks tomorrow's post-market earnings
  - Checks the following day's pre-market earnings
 
## Data Source Integrations

### Using the `-u` Flag (DoltHub and Finnhub)

The `-u` flag enables the use of DoltHub and Finnhub as data sources for earnings calendar information, which can provide more reliable and comprehensive data:

```bash
./run.sh -u [MM/DD/YYYY]
```

or

```bash
python scanner.py -u --date "04/20/2025"
```

### Setting Up DoltHub Integration

1. **Install MySQL Connector**:
   ```bash
   pip install mysql-connector-python
   ```

2. **Install Dolt Database**:
   - Visit [DoltHub's installation guide](https://docs.dolthub.com/getting-started/installation) or use the following:

   For macOS (using Homebrew):
   ```bash
   brew install dolt
   ```

   For Linux/WSL:
   ```bash
   sudo bash -c 'curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh | bash'
   ```

3. **Clone the Earnings Repository**:
   ```bash
   dolt clone dolthub/earnings
   cd earnings
   ```

4. **Start the MySQL Server**:
   ```bash
   dolt sql-server
   ```
   Leave this running in a separate terminal window while using the scanner.

### Setting Up Finnhub Integration

1. **Get a Free API Key**:
   - Visit [Finnhub.io](https://finnhub.io/) and create a free account
   - Go to your dashboard to get your API key

2. **Set Environment Variable**:
   ```bash
   export FINNHUB_API_KEY="your_api_key_here"
   ```

   For persistent use, copy .env.example to .env and add your API key:
   ```dotenv
    FINNHUB_API_KEY=<your_api_key_here>
   ```

### Using All Data Sources

For maximum coverage, you can use the `-c` flag to combine all data sources (Investing.com, DoltHub, and Finnhub):

```bash
./run.sh -c [MM/DD/YYYY]
```

or

```bash
python scanner.py -c --date "04/20/2025"
```

## Troubleshooting
 
Common issues:
 
1. Chrome WebDriver errors:
   - Ensure Google Chrome is installed
   - Try clearing your browser cache
   - Check Chrome version matches driver version
 
2. Rate limiting:
   - The script includes delays to avoid rate limiting
   - If you see connection errors, the tool now has a fallback data source
   - Yahoo Finance API serves as a backup when Investing.com fails

3. Market hours:
   - The scanner uses Eastern Time (ET) for market hours
   - Ensure your system clock is accurate

4. Missing delta information:
   - Some options may not report delta values - the scanner handles this gracefully
   - When no delta values are available, it falls back to strike-based selection

## Performance Optimizations

1. **Filter Chain Ordering**
   - Price check (fastest, immediate exit)
   - Term structure analysis (with early exit)
   - Volume verification
   - Options availability
   - Expiration date check
   - Open interest verification
   - Delta check for ATM options
   - Expected move minimum check
   - Market Chameleon analysis (only performed if other checks pass)
   - IV/RV ratio validation

2. **Parallel Processing**
   - Multi-threaded stock analysis
   - Automatic detection of optimal thread count
   - Configurable via --parallel flag
   - Parallelized earnings data fetching

3. **Browser Efficiency**
   - Reuses single headless browser instance
   - Disables images and unnecessary components
   - Reduced page load timeout
   - Optimized memory usage

4. **Additional Efficiency Improvements**
   - Reduced sleep time between batches (5 seconds)
   - Conditional execution of expensive operations
   - Early exit on critical filter failures
   - List comprehensions for faster data filtering
   - Fallback data sources for reliability
 
## Logs
 
 Logs are stored in the `logs` directory
 Each run creates a dated log file
 Check logs for detailed error information and debugging
