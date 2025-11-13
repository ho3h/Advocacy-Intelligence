"""Scrapy-based web scraper utility.

This module provides a Scrapy-based scraping utility that follows best practices:
- Proper User-Agent headers
- Error handling with retry logic
- Respectful delays
- Anti-bot detection handling

Uses Scrapy's CrawlerProcess for single-page scraping, following Scrapy best practices
for headers, retry logic, and error handling.

Used as the first fallback before HyperBrowser.ai for cost-effective scraping.
"""

import time
import re
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urljoin

# Try to import Scrapy (optional dependency)
try:
    from scrapy import Request
    from scrapy.crawler import CrawlerProcess
    from scrapy.http import Response
    from scrapy.spidermiddlewares.httperror import HttpError
    from twisted.internet.error import DNSLookupError, TimeoutError, TCPTimedOutError
    import scrapy
    SCRAPY_AVAILABLE = True
except ImportError:
    SCRAPY_AVAILABLE = False
    # Create dummy classes to prevent NameError
    class scrapy:
        class Spider:
            pass


if SCRAPY_AVAILABLE:
    class ScrapyScraperSpider(scrapy.Spider):
        """Internal Scrapy spider for single-page scraping."""
        
        name = "single_page_scraper"
        
        def __init__(self, target_url: str, result_container: Optional[Dict[str, Any]] = None, *args, **kwargs):
            """Initialize spider with target URL."""
            super().__init__(*args, **kwargs)
            self.target_url = target_url
            self.result_container = result_container if result_container is not None else {}
            self.result = None
            self.error = None
            
        def start_requests(self):
            """Start the scraping request."""
            yield Request(
                url=self.target_url,
                callback=self.parse,
                errback=self.errback_handler,
                dont_filter=True,
                meta={
                    'handle_httpstatus_all': True,  # Handle all status codes
                    'dont_retry': False,  # Allow retries
                    'max_retry_times': 2,  # Max 2 retries
                },
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
        
        def parse(self, response: Response):
            """Parse the response."""
            # Check for anti-bot indicators
            html_content = response.text.lower()
            block_indicators = ScrapyScraper.BLOCK_INDICATORS
            
            matched_indicator = next((indicator for indicator in block_indicators if indicator in html_content), None)
            if matched_indicator:
                self.error = f"Anti-bot protection detected ({matched_indicator})"
                self.result_container['error'] = self.error
                return
            
            # Check for valid content (not too short)
            if len(response.text) < 500:
                self.error = "Content too short (likely blocked or empty)"
                self.result_container['error'] = self.error
                return
            
            # Check HTTP status (but allow redirects)
            if response.status >= 400 and response.status not in [301, 302, 303, 307, 308]:
                self.error = f"HTTP {response.status} error"
                self.result_container['error'] = self.error
                return
            
            # Success - store result
            self.result = {
                'html': response.text,
                'status': response.status,
                'url': response.url
            }
            self.result_container['result'] = self.result
        
        def errback_handler(self, failure):
            """Handle errors during request."""
            if failure.check(HttpError):
                response = failure.value.response
                self.error = f"HttpError on {response.url}: {response.status}"
            elif failure.check(DNSLookupError):
                request = failure.request
                self.error = f"DNSLookupError on {request.url}"
            elif failure.check(TimeoutError, TCPTimedOutError):
                request = failure.request
                self.error = f"TimeoutError on {request.url}"
            else:
                self.error = f"Unknown error: {failure}"
            self.result_container['error'] = self.error
            return None
else:
    # Dummy class when scrapy is not available
    class ScrapyScraperSpider:
        pass


class ScrapyScraper:
    """Scrapy-based web scraper utility.
    
    Provides a cost-effective alternative to HyperBrowser.ai for scraping
    pages that don't require JavaScript rendering or heavy anti-bot protection.
    
    Best practices implemented:
    - Realistic User-Agent headers
    - Proper error handling with errbacks
    - Retry logic (max 2 retries)
    - Respectful delays
    - Anti-bot detection
    """
    
    # Common anti-bot indicators
    BLOCK_INDICATORS = [
        'checking your browser',
        'access denied',
        'ddos protection',
        'captcha'
    ]
    
    def __init__(self, delay: float = 2.0):
        """
        Initialize Scrapy scraper.
        
        Args:
            delay: Seconds to wait between requests (be respectful)
        """
        self.delay = delay
        
        if not SCRAPY_AVAILABLE:
            raise ImportError(
                "Scrapy is not installed. Install with: pip install scrapy"
            )
    
    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL using Scrapy.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dict with 'html', 'status', 'url' keys, or None if failed
        """
        if not SCRAPY_AVAILABLE:
            return None
        
        try:
            result_container: Dict[str, Any] = {}
            
            # Create crawler process with Scrapy best practices
            process = CrawlerProcess({
                'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'ROBOTSTXT_OBEY': False,  # Don't check robots.txt (we're being respectful with delays)
                'DOWNLOAD_DELAY': self.delay,
                'RANDOMIZE_DOWNLOAD_DELAY': True,  # Add randomness to delays (0.5 * delay to 1.5 * delay)
                'CONCURRENT_REQUESTS': 1,  # One request at a time
                'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
                'RETRY_ENABLED': True,
                'RETRY_TIMES': 2,  # Retry up to 2 times (3 total attempts)
                'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429],  # Retry on these codes
                'HTTPERROR_ALLOWED_CODES': [200, 301, 302, 303, 307, 308],  # Allow redirects
                'LOG_LEVEL': 'ERROR',  # Suppress Scrapy logs
                'TELNETCONSOLE_ENABLED': False,
                'COOKIES_ENABLED': True,  # Enable cookies for session handling
            })
            
            # Run crawler (this is blocking)
            process.crawl(ScrapyScraperSpider, target_url=url, result_container=result_container)
            process.start()
            
            # Check result
            error = result_container.get('error')
            if error:
                print(f"    ⚠ Scrapy error for {url}: {error}")
                return None
            
            if 'result' in result_container:
                return result_container['result']
            
            return None
            
        except Exception as e:
            print(f"    ⚠ Scrapy exception for {url}: {e}")
            return None
    
    def scrape_reference(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a customer reference page.
        
        Args:
            url: URL of customer reference page
            
        Returns:
            Dict with raw_text, url, customer_name, scraped_date, word_count, method
            or None if failed
        """
        result = self.scrape_url(url)
        
        if not result:
            return None
        
        html_content = result['html']
        
        # Check for anti-bot indicators
        html_lower = html_content.lower()
        if any(indicator in html_lower for indicator in self.BLOCK_INDICATORS):
            return None
        
        # Check content quality
        if len(html_content) < 500:
            return None
        
        # Extract text from HTML (simple approach - can be improved with BeautifulSoup)
        # Remove script and style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract text content (simple regex-based extraction)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_content)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Extract customer name from text or URL
        customer_name = "Unknown"
        lines = text.split('\n')
        
        # Try multiple patterns for customer name
        for line in lines[:15]:  # Check first 15 lines
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                # Look for company names in title-like lines
                if any(word in line.lower() for word in ['uses', 'with', 'customer', 'case study', 'success', 'story']):
                    parts = re.split(r'\s+(?:uses|with|customer|case study|success|story)', line, flags=re.IGNORECASE)
                    if parts and parts[0]:
                        potential_name = parts[0].strip()
                        if len(potential_name) > 3 and len(potential_name) < 50:
                            customer_name = potential_name
                            break
        
        # Fallback: try to extract from URL
        if customer_name == "Unknown":
            url_parts = url.split('/')
            # Common patterns: /customers/{name}, /case-study/{name}, etc.
            for part in reversed(url_parts):
                if part and part not in ['customers', 'customer-case-studies', 'case-study', 'case-studies', 
                                        'https:', 'http:', '', 'www']:
                    potential_name = part.replace('-', ' ').title()
                    if len(potential_name) > 2:
                        customer_name = potential_name
                        break
        
        # Clean up text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        raw_text = '\n'.join(lines)
        
        word_count = len(raw_text.split())
        
        return {
            'url': url,
            'customer_name': customer_name,
            'raw_text': raw_text,
            'raw_html': html_content,  # Store original HTML
            'scraped_date': datetime.now().isoformat(),
            'word_count': word_count,
            'method': 'scrapy'
        }


def scrape_with_scrapy(url: str, delay: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Convenience function to scrape a URL with Scrapy.
    
    Args:
        url: URL to scrape
        delay: Seconds to wait between requests
        
    Returns:
        Dict with scraped data or None if failed
    """
    if not SCRAPY_AVAILABLE:
        return None
    
    scraper = ScrapyScraper(delay=delay)
    return scraper.scrape_reference(url)


if __name__ == '__main__':
    # Test scraper
    if SCRAPY_AVAILABLE:
        scraper = ScrapyScraper()
        test_url = "https://www.snowflake.com/en/customers/all-customers/"
        print(f"Testing Scrapy scraper with: {test_url}")
        result = scraper.scrape_reference(test_url)
        if result:
            print(f"\n✓ Successfully scraped:")
            print(f"  Customer: {result['customer_name']}")
            print(f"  Word count: {result['word_count']}")
            print(f"  Content preview: {result['raw_text'][:200]}...")
        else:
            print("\n✗ Failed to scrape")
    else:
        print("Scrapy is not installed. Install with: pip install scrapy")

