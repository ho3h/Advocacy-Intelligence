"""Simple sitemap-based URL discovery for customer reference pages.

This is much simpler than pagination scraping - just fetch sitemaps and filter URLs!
Works great for MongoDB, Redis (if they have sitemaps), and other vendors.
"""

import re
import requests
import xml.etree.ElementTree as ET
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse


def fetch_sitemap(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch sitemap XML content from URL.
    
    Args:
        url: Sitemap URL (e.g., https://example.com/sitemap.xml)
        timeout: Request timeout in seconds
        
    Returns:
        XML content as string, or None if failed
    """
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SitemapBot/1.0)'
        })
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  ⚠ Failed to fetch {url}: {e}")
        return None


def parse_sitemap_urls(xml_content: str) -> List[str]:
    """Extract all URLs from a sitemap XML.
    
    Handles both regular sitemaps and sitemap index files.
    
    Args:
        xml_content: XML content as string
        
    Returns:
        List of URLs found in sitemap
    """
    urls = []
    
    try:
        root = ET.fromstring(xml_content)
        
        # Handle sitemap index (contains references to other sitemaps)
        if root.tag.endswith('sitemapindex'):
            for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc_elem = sitemap_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text)
        # Handle regular sitemap (contains page URLs)
        elif root.tag.endswith('urlset'):
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text)
        else:
            # Try without namespace (some sites don't use proper namespaces)
            for url_elem in root.findall('.//url'):
                loc_elem = url_elem.find('loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text)
            for sitemap_elem in root.findall('.//sitemap'):
                loc_elem = sitemap_elem.find('loc')
                if loc_elem is not None and loc_elem.text:
                    urls.append(loc_elem.text)
                    
    except ET.ParseError as e:
        print(f"  ⚠ XML parse error: {e}")
        # Fallback: use regex to extract URLs
        url_pattern = r'<loc>(.*?)</loc>'
        urls = re.findall(url_pattern, xml_content, re.IGNORECASE)
    
    return urls


def filter_customer_urls(urls: List[str], patterns: List[str], exclude_patterns: Optional[List[str]] = None) -> List[str]:
    """Filter URLs to find customer reference pages.
    
    Args:
        urls: List of URLs to filter
        patterns: List of regex patterns to match (e.g., [r'/customers/', r'/case-study/'])
        exclude_patterns: List of patterns to exclude (e.g., [r'/customers/$', r'#'])
        
    Returns:
        Filtered list of customer reference URLs
    """
    if exclude_patterns is None:
        exclude_patterns = []
    
    customer_urls = []
    
    for url in urls:
        url_lower = url.lower()
        
        # Check if URL matches any pattern
        matches = False
        for pattern in patterns:
            if re.search(pattern, url_lower):
                matches = True
                break
        
        if not matches:
            continue
        
        # Check if URL should be excluded
        excluded = False
        for exclude_pattern in exclude_patterns:
            if re.search(exclude_pattern, url_lower):
                excluded = True
                break
        
        if not excluded:
            customer_urls.append(url)
    
    return sorted(set(customer_urls))  # Remove duplicates and sort


def discover_from_sitemap(
    base_url: str,
    sitemap_path: str = '/sitemap.xml',
    url_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    follow_sitemap_index: bool = True,
    max_sitemaps: int = 10
) -> List[str]:
    """Discover customer reference URLs from sitemap(s).
    
    Args:
        base_url: Base URL of the website (e.g., 'https://redis.io')
        sitemap_path: Path to sitemap (e.g., '/sitemap.xml')
        url_patterns: Patterns to match customer URLs (default: common patterns)
        exclude_patterns: Patterns to exclude (default: listing pages, filters)
        follow_sitemap_index: If True, follow sitemap index files to child sitemaps
        max_sitemaps: Maximum number of sitemaps to process (safety limit)
        
    Returns:
        List of customer reference URLs
        
    Example:
        >>> urls = discover_from_sitemap(
        ...     'https://redis.io',
        ...     url_patterns=[r'/customers/'],
        ...     exclude_patterns=[r'/customers/$', r'\?', r'#']
        ... )
    """
    if url_patterns is None:
        # Default patterns for common customer reference URL structures
        url_patterns = [
            r'/customers/',
            r'/customer/',
            r'/case-study/',
            r'/case-studies/',
            r'/customer-story/',
            r'/customer-stories/',
            r'/success-story/',
            r'/success-stories/',
        ]
    
    if exclude_patterns is None:
        # Default exclusions: listing pages, filters, anchors
        exclude_patterns = [
            r'/customers/?$',  # Base customers listing page
            r'/customer/?$',
            r'/case-studies/?$',
            r'/customer-stories/?$',
            r'\?',  # Query parameters (filter pages)
            r'#',   # Anchors
            r'/tag/',  # Tag pages
            r'/category/',  # Category pages
        ]
    
    sitemap_url = urljoin(base_url, sitemap_path)
    print(f"📄 Fetching sitemap: {sitemap_url}")
    
    xml_content = fetch_sitemap(sitemap_url)
    if not xml_content:
        print("  ✗ Could not fetch sitemap")
        return []
    
    all_urls = []
    sitemaps_processed = 0
    
    # Check if this is a sitemap index
    urls_from_sitemap = parse_sitemap_urls(xml_content)
    
    if follow_sitemap_index and any('sitemap' in url.lower() for url in urls_from_sitemap):
        print(f"  ✓ Found sitemap index with {len(urls_from_sitemap)} child sitemaps")
        # This is a sitemap index - fetch child sitemaps
        for child_sitemap_url in urls_from_sitemap[:max_sitemaps]:
            if sitemaps_processed >= max_sitemaps:
                break
            print(f"  → Fetching child sitemap: {child_sitemap_url}")
            child_xml = fetch_sitemap(child_sitemap_url)
            if child_xml:
                child_urls = parse_sitemap_urls(child_xml)
                all_urls.extend(child_urls)
                print(f"    ✓ Found {len(child_urls)} URLs")
            sitemaps_processed += 1
    else:
        # Regular sitemap - use URLs directly
        all_urls = urls_from_sitemap
        print(f"  ✓ Found {len(all_urls)} URLs in sitemap")
    
    # Filter for customer reference URLs
    customer_urls = filter_customer_urls(all_urls, url_patterns, exclude_patterns)
    
    print(f"  ✓ Filtered to {len(customer_urls)} customer reference URLs")
    
    return customer_urls


# Vendor-specific configurations
VENDOR_CONFIGS = {
    'redis': {
        'base_url': 'https://redis.io',
        'sitemap_path': '/sitemap.xml',
        'url_patterns': [r'/customers/'],
        'exclude_patterns': [r'/customers/?$', r'\?', r'#'],
    },
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
    'databricks': {
        'base_url': 'https://www.databricks.com',
        'sitemap_path': '/webshared/sitemaps/sitemap-index.xml',
        'url_patterns': [r'/customers/'],
        'exclude_patterns': [
            r'/customers/?$',  # Base customers listing page
            r'/customers/gen-ai',  # Special pages
            r'/customers/your-ai',
            r'/customers/champions-program',
            r'/customers/solutions-accelerator-general',
            r'\?',  # Query parameters
            r'#',   # Anchors
        ],
        'follow_sitemap_index': True,
        'max_sitemaps': 20,  # Limit to customer sitemap
    },
}


def discover_vendor_urls(vendor: str) -> List[str]:
    """Discover customer reference URLs for a known vendor.
    
    Args:
        vendor: Vendor name ('redis', 'mongodb', 'databricks', etc.)
        
    Returns:
        List of customer reference URLs
        
    Example:
        >>> urls = discover_vendor_urls('redis')
    """
    vendor_lower = vendor.lower()
    
    if vendor_lower not in VENDOR_CONFIGS:
        raise ValueError(
            f"Unknown vendor: {vendor}. Known vendors: {list(VENDOR_CONFIGS.keys())}"
        )
    
    config = VENDOR_CONFIGS[vendor_lower]
    
    # Handle sitemap index following for Databricks
    follow_index = config.get('follow_sitemap_index', True)
    max_sitemaps = config.get('max_sitemaps', 10)
    
    # For Databricks, we need to filter to only the customer sitemap
    if vendor_lower == 'databricks':
        # First, get the main sitemap index
        sitemap_index_url = config['base_url'] + config['sitemap_path']
        index_xml = fetch_sitemap(sitemap_index_url)
        if index_xml:
            index_urls = parse_sitemap_urls(index_xml)
            # Find the customer sitemap index
            customer_sitemap_index = None
            for sitemap_url in index_urls:
                if 'customer-assets' in sitemap_url.lower() and 'sitemap-index' in sitemap_url.lower():
                    customer_sitemap_index = sitemap_url
                    break
            
            if customer_sitemap_index:
                # Fetch the customer sitemap index (which points to child sitemaps)
                customer_index_xml = fetch_sitemap(customer_sitemap_index)
                if customer_index_xml:
                    customer_sitemap_urls = parse_sitemap_urls(customer_index_xml)
                    # Fetch the actual customer sitemap (usually sitemap-0.xml)
                    all_urls = []
                    for sitemap_url in customer_sitemap_urls[:max_sitemaps]:
                        sitemap_xml = fetch_sitemap(sitemap_url)
                        if sitemap_xml:
                            urls = parse_sitemap_urls(sitemap_xml)
                            all_urls.extend(urls)
                    
                    # Filter for customer URLs
                    customer_urls = filter_customer_urls(
                        all_urls,
                        config['url_patterns'],
                        config['exclude_patterns']
                    )
                    return customer_urls
    
    # Default behavior for other vendors
    return discover_from_sitemap(
        base_url=config['base_url'],
        sitemap_path=config['sitemap_path'],
        url_patterns=config['url_patterns'],
        exclude_patterns=config['exclude_patterns'],
        follow_sitemap_index=follow_index,
        max_sitemaps=max_sitemaps,
    )


if __name__ == '__main__':
    """Command-line usage examples."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python sitemap_discovery.py redis")
        print("  python sitemap_discovery.py mongodb")
        print("  python sitemap_discovery.py <base_url> <sitemap_path>")
        sys.exit(1)
    
    if sys.argv[1] in VENDOR_CONFIGS:
        # Use predefined vendor config
        vendor = sys.argv[1]
        print(f"🔍 Discovering URLs for {vendor}...")
        urls = discover_vendor_urls(vendor)
    else:
        # Custom URL
        base_url = sys.argv[1]
        sitemap_path = sys.argv[2] if len(sys.argv) > 2 else '/sitemap.xml'
        print(f"🔍 Discovering URLs from {base_url}{sitemap_path}...")
        urls = discover_from_sitemap(base_url, sitemap_path)
    
    print(f"\n✓ Found {len(urls)} customer reference URLs:")
    for url in urls[:10]:  # Show first 10
        print(f"  - {url}")
    if len(urls) > 10:
        print(f"  ... and {len(urls) - 10} more")

