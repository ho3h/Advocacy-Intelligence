"""Discover and save Snowflake customer reference URLs (Phase 1 only)."""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.snowflake_scraper import SnowflakeScraper


def main():
    """Run Phase 1: URL Discovery and save URLs to file."""
    
    print("=" * 70)
    print("SNOWFLAKE URL DISCOVERY (PHASE 1)")
    print("=" * 70)
    
    # Initialize scraper
    scraper = SnowflakeScraper(delay=2)
    
    # Discover URLs
    urls = scraper.get_customer_reference_urls()
    
    if not urls:
        print("✗ No URLs found")
        return
    
    # Save URLs to file in the same location structure as scraped pages
    vendor_name = 'Snowflake'
    output_dir = os.path.join('data', 'scraped', vendor_name.lower())
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = os.path.join(output_dir, f'discovered_urls-{timestamp}.json')
    
    # Save as JSON with metadata
    data = {
        'vendor': vendor_name,
        'discovery_date': datetime.now().isoformat(),
        'total_urls': len(urls),
        'urls': urls
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved {len(urls)} URLs to: {output_file}")
    print(f"📁 Full path: {os.path.abspath(output_file)}")
    
    # Also save as simple text file (one URL per line) for easy inspection
    txt_file = output_file.replace('.json', '.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(urls))
    
    print(f"📄 Also saved as text file: {txt_file}")
    print(f"\n✓ URL discovery complete! Found {len(urls)} customer reference URLs")
    print(f"  Files saved in: {output_dir}/")


if __name__ == '__main__':
    main()

