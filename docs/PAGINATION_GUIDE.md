# Flexible Pagination System for Multi-Vendor Scraping

## Overview

The pagination system is designed to work across different vendors with varying pagination patterns. Each vendor can use a different strategy while sharing the same completion detection logic.

## Pagination Strategies

### 1. Offset-Based Pagination (Snowflake)
Uses query parameters: `?page=0&pageSize=12&offset=0`

```python
from scrapers.pagination import OffsetPaginationStrategy

strategy = OffsetPaginationStrategy(
    pagination_path="/en/customers/all-customers/",
    page_param="page",
    page_size_param="pageSize",
    offset_param="offset"
)
```

### 2. Page Number Pagination (Databricks, AWS)
Uses simple page numbers: `?page=1`, `?page=2`

```python
from scrapers.pagination import PageNumberPaginationStrategy

strategy = PageNumberPaginationStrategy(
    pagination_path="/customers/",
    page_param="page",
    start_at=1  # Pages start at 1, not 0
)
```

### 3. Path-Based Pagination (GCP, some WordPress sites)
Uses path segments: `/customers/page/1`, `/customers/page/2`

```python
from scrapers.pagination import PathPaginationStrategy

strategy = PathPaginationStrategy(
    pagination_path_template="/customers/page/{page}",
    start_at=1
)
```

## Completion Detection

The system automatically detects when all pages are scraped using multiple heuristics:

### 1. **Duplicate URL Detection** (Primary)
- Tracks unique URLs across pages
- Stops when a page returns only duplicates (looped back)
- Works for: All vendors

### 2. **Empty Page Detection** (Secondary)
- Stops after N consecutive empty pages
- Configurable threshold (default: 2)
- Works for: All vendors

### 3. **Total Count Detection** (Future)
- Parse total count from page HTML
- Stop when reached expected count
- Requires vendor-specific selector

## Configuration Options

```python
from scrapers.pagination import PaginationConfig

config = PaginationConfig(
    page_size=12,                    # Items per page
    max_consecutive_empty=2,         # Stop after N empty pages
    max_pages=None,                   # Optional limit (None = auto-detect)
    safety_limit=100,                 # Absolute maximum pages
    check_duplicates=True,            # Enable duplicate detection
    check_empty_pages=True,           # Enable empty page detection
    check_total_count=False,          # Future: parse total count
    total_count_selector=None         # CSS selector for total count
)
```

## Example: Adding a New Vendor

### Databricks Example

```python
from scrapers.pagination import (
    PageNumberPaginationStrategy,
    PaginationConfig,
    paginate_with_strategy
)

class DatabricksScraper:
    BASE_URL = "https://www.databricks.com"
    
    def __init__(self):
        # ... initialize HyperBrowser client ...
        pass
    
    def _extract_case_study_links(self, soup, base_url):
        """Extract Databricks-specific case study links."""
        links = set()
        # Vendor-specific link extraction logic
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/customer-stories/' in href.lower():
                links.add(urljoin(base_url, href))
        return links
    
    def _fetch_page(self, url):
        """Fetch page using HyperBrowser.ai."""
        # ... vendor-specific fetching logic ...
        return soup
    
    def get_customer_reference_urls(self, max_pages=None):
        """Get all customer reference URLs."""
        # Use page number pagination (Databricks style)
        strategy = PageNumberPaginationStrategy(
            pagination_path="/customers/",
            page_param="page",
            start_at=1  # Databricks pages start at 1
        )
        
        config = PaginationConfig(
            page_size=20,  # Databricks shows 20 per page
            max_pages=max_pages,
            check_duplicates=True,
            check_empty_pages=True
        )
        
        return paginate_with_strategy(
            strategy=strategy,
            link_extractor=self._extract_case_study_links,
            page_fetcher=self._fetch_page,
            base_url=self.BASE_URL,
            config=config
        )
```

### AWS Example

```python
class AWSScraper:
    BASE_URL = "https://aws.amazon.com"
    
    def get_customer_reference_urls(self, max_pages=None):
        """AWS uses different pagination - might need custom strategy."""
        # AWS might use infinite scroll or different pattern
        # Could extend PaginationStrategy for vendor-specific logic
        strategy = PageNumberPaginationStrategy(
            pagination_path="/solutions/case-studies/",
            page_param="page"
        )
        
        config = PaginationConfig(
            page_size=10,
            max_pages=max_pages
        )
        
        return paginate_with_strategy(
            strategy=strategy,
            link_extractor=self._extract_aws_links,
            page_fetcher=self._fetch_page,
            base_url=self.BASE_URL,
            config=config
        )
```

### Fivetran Example (Simple List)

```python
class FivetranScraper:
    BASE_URL = "https://www.fivetran.com"
    
    def get_customer_reference_urls(self, max_pages=None):
        """Fivetran might have all customers on one page."""
        # If no pagination, return single page
        soup = self._fetch_page(f"{self.BASE_URL}/customers")
        return list(self._extract_fivetran_links(soup, self.BASE_URL))
```

## Custom Strategies

For vendors with unique pagination patterns, extend `PaginationStrategy`:

```python
class CustomPaginationStrategy(PaginationStrategy):
    """Custom strategy for vendor-specific pagination."""
    
    def build_url(self, base_url: str, page_num: int, page_size: int) -> str:
        # Custom URL building logic
        return f"{base_url}/customers?custom_param={page_num * page_size}"
    
    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        # Custom link extraction logic
        links = set()
        # ... vendor-specific extraction ...
        return links
    
    def should_stop(self, page_links, all_links, page_num, consecutive_empty, config, soup):
        # Optionally override completion detection
        # Otherwise uses default logic from base class
        return super().should_stop(page_links, all_links, page_num, consecutive_empty, config, soup)
```

## Testing Pagination

Test pagination strategies independently:

```python
# Test with limited pages first
urls = scraper.get_customer_reference_urls(max_pages=3)
print(f"Found {len(urls)} URLs in first 3 pages")

# Then run full scrape
urls = scraper.get_customer_reference_urls()  # Auto-detect completion
print(f"Found {len(urls)} total URLs")
```

## Common Patterns by Vendor

| Vendor | Pagination Type | Page Size | Start At | Notes |
|--------|----------------|-----------|----------|-------|
| Snowflake | Offset | 12 | 0 | Uses offset parameter |
| Databricks | Page Number | 20 | 1 | Simple page numbers |
| AWS | Page Number | 10 | 1 | May use infinite scroll |
| GCP | Path-based | 12 | 1 | `/customers/page/{n}` |
| Fivetran | Single Page | N/A | N/A | All on one page |
| MongoDB | Page Number | 15 | 1 | Standard pagination |

## Benefits

1. **Reusable Logic**: Completion detection works across all vendors
2. **Vendor-Specific**: Each vendor defines only URL building and link extraction
3. **Testable**: Can test pagination independently of scraping
4. **Extensible**: Easy to add new strategies for unique patterns
5. **Configurable**: Adjust completion detection per vendor needs

## Future Enhancements

- **Total Count Detection**: Parse "Showing 1-12 of 245" to know when done
- **Infinite Scroll Support**: Handle JavaScript-loaded pagination
- **Rate Limit Detection**: Stop if hitting rate limits
- **Progress Tracking**: Save progress and resume from last page

