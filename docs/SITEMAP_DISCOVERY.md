# Sitemap-Based URL Discovery

## Overview

This is a **much simpler** approach than pagination scraping! Instead of clicking through pages or handling "Load More" buttons, we just:

1. Fetch the website's sitemap(s)
2. Parse all URLs from the XML
3. Filter for customer reference URLs using regex patterns

**Result**: Fast, reliable, and works great for most vendors!

## Usage

### Command Line

```bash
# For MongoDB (works great!)
python scripts/discover_urls_sitemap.py mongodb

# For Redis (may need HyperBrowser.ai fallback if Cloudflare blocks)
python scripts/discover_urls_sitemap.py redis
```

### Python Code

```python
from src.utils.sitemap_discovery import discover_vendor_urls, discover_from_sitemap

# Use predefined vendor config
urls = discover_vendor_urls('mongodb')

# Or customize
urls = discover_from_sitemap(
    base_url='https://example.com',
    sitemap_path='/sitemap.xml',
    url_patterns=[r'/customers/', r'/case-study/'],
    exclude_patterns=[r'/customers/?$', r'\?', r'#']
)
```

## When to Use Sitemap vs Pagination

### ✅ Use Sitemap When:
- Website has a sitemap (most modern sites do)
- Sitemap is accessible (not behind Cloudflare/anti-bot)
- Customer URLs follow predictable patterns (e.g., `/customers/{name}/`)

**Examples**: MongoDB, Databricks, most modern websites

### ⚠️ Use Pagination When:
- No sitemap available
- Sitemap is behind Cloudflare/anti-bot protection
- Customer URLs are dynamically loaded via JavaScript
- Sitemap doesn't include customer pages

**Examples**: Redis (Cloudflare protection), some older sites

## Results

### MongoDB
- **Found**: 294 customer reference URLs
- **Method**: Sitemap (works perfectly!)
- **Time**: ~10 seconds

### Redis
- **Status**: Cloudflare protection (522 error)
- **Fallback**: Use pagination scraper with HyperBrowser.ai

## Configuration

Vendor configurations are in `src/utils/sitemap_discovery.py`:

```python
VENDOR_CONFIGS = {
    'mongodb': {
        'base_url': 'https://www.mongodb.com',
        'sitemap_path': '/sitemap.xml',
        'url_patterns': [
            r'/solutions/customer-case-studies/',
            r'/customers/',
            r'/case-study/',
        ],
        'exclude_patterns': [
            r'/solutions/customer-case-studies/?$',
            r'/customers/?$',
            r'\?',
            r'#',
        ],
    },
    # Add more vendors here...
}
```

## Advantages

1. **Fast**: Single HTTP request vs. dozens of paginated requests
2. **Simple**: No JavaScript rendering needed
3. **Reliable**: Sitemaps are standardized XML
4. **Complete**: Gets all URLs at once (no pagination logic)
5. **Cheap**: No API costs (unlike HyperBrowser.ai)

## Limitations

1. **Requires sitemap**: Some sites don't have one
2. **Cloudflare protection**: Some sites block sitemap access
3. **Pattern matching**: Need to know URL patterns (but easy to discover)

## Adding New Vendors

1. Check if vendor has sitemap:
   ```bash
   curl -I https://vendor.com/sitemap.xml
   ```

2. If yes, add config to `VENDOR_CONFIGS`:
   ```python
   'newvendor': {
       'base_url': 'https://newvendor.com',
       'sitemap_path': '/sitemap.xml',
       'url_patterns': [r'/customers/', r'/case-study/'],
       'exclude_patterns': [r'/customers/?$', r'\?'],
   }
   ```

3. Test:
   ```bash
   python scripts/discover_urls_sitemap.py newvendor
   ```

## Comparison: Sitemap vs Pagination

| Feature | Sitemap | Pagination |
|---------|---------|------------|
| Speed | ⚡ Fast (seconds) | 🐌 Slow (minutes) |
| Complexity | ✅ Simple | ❌ Complex |
| Cost | 💰 Free | 💰💰 HyperBrowser.ai costs |
| Reliability | ✅ High | ⚠️ Depends on site |
| Works with Cloudflare | ❌ Usually blocked | ✅ With HyperBrowser.ai |
| JavaScript needed | ❌ No | ✅ Yes |

## Recommendation

**Always try sitemap first!** If it works, you're done. If not, fall back to pagination scraping.

For MongoDB: ✅ Use sitemap (works perfectly)
For Redis: ⚠️ Use pagination (Cloudflare blocks sitemap)

