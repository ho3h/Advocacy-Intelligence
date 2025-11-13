"""Test scraping a single customer reference page using UniversalScraper."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pipeline.scraper_registry import get_scraper
from pipeline.vendor_config import get_enabled_vendors


def main():
    print("=" * 60)
    print("TESTING SINGLE PAGE SCRAPING")
    print("=" * 60)
    
    # Get first available vendor for testing
    enabled_vendors = get_enabled_vendors()
    if not enabled_vendors:
        print("✗ No enabled vendors found in configuration")
        return
    
    vendor_key = enabled_vendors[0]
    print(f"\nUsing vendor: {vendor_key}")
    
    try:
        scraper = get_scraper(vendor_key)
    except Exception as e:
        print(f"✗ Failed to get scraper: {e}")
        return
    
    # Get URLs first
    print("\n1. Discovering customer reference URLs...")
    try:
        urls = scraper.get_customer_reference_urls()
    except NotImplementedError:
        print("⚠ This vendor uses sitemap discovery (not pagination)")
        print("   Use: python scripts/run_pipeline.py --vendors {} --phases 1".format(vendor_key))
        return
    
    if not urls:
        print("✗ No URLs found")
        return
    
    print(f"\n✓ Found {len(urls)} URLs")
    print("\nFirst 5 URLs:")
    for i, url in enumerate(urls[:5], 1):
        print(f"  {i}. {url}")
    
    # Test scraping the first URL
    test_url = urls[0]
    print(f"\n2. Testing scrape of first URL:")
    print(f"   {test_url}")
    print("\n   (This may take 10-30 seconds with HyperBrowser.ai)...")
    
    result = scraper.scrape_reference(test_url)
    
    if result:
        print("\n✓ SUCCESS!")
        print(f"\n   Customer: {result['customer_name']}")
        print(f"   Method: {result.get('method', 'unknown')}")
        print(f"   Word count: {result['word_count']}")
        print(f"\n   Text preview (first 300 chars):")
        print(f"   {result['raw_text'][:300]}...")
    else:
        print("\n✗ FAILED - Could not scrape this page")
        print("   This might indicate:")
        print("   - Page requires special authentication")
        print("   - Page structure is different than expected")
        print("   - HyperBrowser.ai needs different configuration")


if __name__ == '__main__':
    main()
