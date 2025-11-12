"""Test scraping short URLs to see if they have full content."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.snowflake_scraper import SnowflakeScraper

# URLs that returned short content (< 100 words)
SHORT_URLS = [
    "https://www.snowflake.com/en/customers/all-customers/case-study/rac/",
    "https://www.snowflake.com/en/customers/all-customers/case-study/penske/",
    "https://www.snowflake.com/en/customers/all-customers/case-study/power-digital/",
    "https://www.snowflake.com/en/customers/all-customers/case-study/aviva/",
    "https://www.snowflake.com/en/customers/all-customers/case-study/bmw-group/",
]

def main():
    print("=" * 60)
    print("TESTING SHORT URLs")
    print("=" * 60)
    
    scraper = SnowflakeScraper(delay=2)
    
    if not scraper.hb_client:
        print("✗ HyperBrowser.ai not available")
        return
    
    print(f"\nTesting {len(SHORT_URLS)} URLs that previously returned < 100 words...\n")
    
    for i, url in enumerate(SHORT_URLS, 1):
        print(f"\n[{i}/{len(SHORT_URLS)}] Testing: {url}")
        print("-" * 60)
        
        result = scraper.scrape_reference(url)
        
        if result:
            print(f"\n✓ Scraped successfully")
            print(f"  Word count: {result['word_count']}")
            print(f"  Customer name: {result['customer_name']}")
            print(f"\n  First 500 characters of content:")
            print(f"  {'-' * 58}")
            preview = result['raw_text'][:500]
            print(f"  {preview}")
            print(f"  {'-' * 58}")
            
            if result['word_count'] < 100:
                print(f"\n  ⚠ Still short ({result['word_count']} words) - likely incomplete")
            else:
                print(f"\n  ✓ Got full content ({result['word_count']} words)")
        else:
            print(f"\n✗ Failed to scrape")
        
        if i < len(SHORT_URLS):
            import time
            time.sleep(3)  # Be respectful

if __name__ == '__main__':
    main()

