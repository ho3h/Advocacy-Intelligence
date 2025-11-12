"""Discover customer reference URLs using sitemap (simple approach).

This is much simpler than pagination scraping - just fetch sitemaps and filter URLs!
Works great for MongoDB, Redis (if they have sitemaps), and other vendors.

Usage:
    python scripts/discover_urls_sitemap.py redis
    python scripts/discover_urls_sitemap.py mongodb
    python scripts/discover_urls_sitemap.py <vendor_name>
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.sitemap_discovery import discover_vendor_urls, VENDOR_CONFIGS


def main():
    """Run sitemap-based URL discovery and save URLs to file."""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  python {sys.argv[0]} <vendor>")
        print(f"\nAvailable vendors: {', '.join(VENDOR_CONFIGS.keys())}")
        print("\nExample:")
        print(f"  python {sys.argv[0]} redis")
        print(f"  python {sys.argv[0]} mongodb")
        sys.exit(1)
    
    vendor_name = sys.argv[1].lower()
    
    if vendor_name not in VENDOR_CONFIGS:
        print(f"✗ Unknown vendor: {vendor_name}")
        print(f"Available vendors: {', '.join(VENDOR_CONFIGS.keys())}")
        sys.exit(1)
    
    print("=" * 70)
    print(f"SITEMAP-BASED URL DISCOVERY: {vendor_name.upper()}")
    print("=" * 70)
    print("\nThis approach is much simpler than pagination scraping!")
    print("We just fetch the sitemap and filter for customer URLs.\n")
    
    # Discover URLs
    try:
        urls = discover_vendor_urls(vendor_name)
    except Exception as e:
        print(f"✗ Error discovering URLs: {e}")
        sys.exit(1)
    
    if not urls:
        print("✗ No URLs found")
        print("\nPossible reasons:")
        print("  - Sitemap doesn't exist or isn't accessible")
        print("  - Customer URLs don't match the expected patterns")
        print("  - Try checking the sitemap manually:")
        config = VENDOR_CONFIGS[vendor_name]
        print(f"    {config['base_url']}{config['sitemap_path']}")
        return
    
    # Save URLs to file
    output_dir = os.path.join('data', 'scraped', vendor_name.lower())
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = os.path.join(output_dir, f'discovered_urls-sitemap-{timestamp}.json')
    
    # Save as JSON with metadata
    data = {
        'vendor': vendor_name,
        'discovery_method': 'sitemap',
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
    print(f"\n💡 Tip: Compare with pagination-based discovery to see which finds more URLs!")


if __name__ == '__main__':
    main()

