# Hybrid Scraper Implementation

The `SnowflakeScraper` now uses a hybrid approach: **BeautifulSoup first, HyperBrowser.ai fallback**.

## How It Works

1. **Primary Method (BeautifulSoup)**: Fast, free HTML parsing
   - Tries to scrape with `requests` + `BeautifulSoup`
   - Checks for anti-bot blocks automatically
   - Validates content quality (minimum 50 words)

2. **Fallback Method (HyperBrowser.ai)**: When BeautifulSoup fails
   - Automatically triggered if:
     - Page is blocked by anti-bot protection
     - Content is suspiciously short (< 50 words)
     - Network/timeout errors occur
   - Uses stealth mode and JavaScript rendering
   - Extracts markdown/text content

## Configuration

### Option 1: BeautifulSoup Only (Free)
```python
scraper = SnowflakeScraper(
    delay=2,
    use_hyperbrowser_fallback=False  # Disable fallback
)
```

### Option 2: With HyperBrowser.ai Fallback
```python
# Set HYPERBROWSER_API_KEY in .env
scraper = SnowflakeScraper(
    delay=2,
    use_hyperbrowser_fallback=True  # Default
)
```

## Output

Each scraped reference includes a `method` field:
- `method: 'beautifulsoup'` - Scraped with BeautifulSoup
- `method: 'hyperbrowser'` - Scraped with HyperBrowser.ai fallback

## Cost Optimization

- **Most pages**: Scraped for free with BeautifulSoup
- **Blocked pages**: Only pay for HyperBrowser.ai when needed
- **Estimated cost**: ~$0-5 for 100 references (depending on block rate)

## Block Detection

The scraper automatically detects common anti-bot indicators:
- Cloudflare challenges
- "Checking your browser" messages
- Access denied pages
- Suspiciously short content (< 200 chars)

## Usage Example

```python
from scrapers.snowflake_scraper import SnowflakeScraper

# Initialize with fallback enabled
scraper = SnowflakeScraper(delay=2)

# Scrape all references
references = scraper.scrape_all()

# Check which method was used
for ref in references:
    print(f"{ref['customer_name']}: {ref['method']}")
```

