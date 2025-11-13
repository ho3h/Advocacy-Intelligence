"""Registry for mapping vendor names to scraper instances using UniversalScraper."""

from typing import Optional, Dict
from .vendor_config import get_vendor_config
from scrapers.universal_scraper import UniversalScraper


def get_scraper(vendor_key: str):
    """
    Get scraper instance for a vendor using UniversalScraper.
    
    Args:
        vendor_key: Vendor key (e.g., 'mongodb', 'snowflake')
        
    Returns:
        UniversalScraper instance configured for the vendor
        
    Raises:
        ValueError: If vendor not found in configuration
    """
    vendor_key = vendor_key.lower()
    
    # Get vendor configuration
    vendor_config = get_vendor_config(vendor_key)
    if not vendor_config:
        from .vendor_config import get_enabled_vendors
        available = ', '.join(get_enabled_vendors())
        raise ValueError(
            f"Vendor '{vendor_key}' not found in vendor configuration. "
            f"Available vendors: {available}. Check data/vendors.json"
        )
    
    # Create UniversalScraper instance with vendor config
    scraper = UniversalScraper(vendor_config=vendor_config, delay=2)
    
    return scraper


def list_registered_vendors() -> list:
    """
    Get list of all registered vendor keys.
    
    Returns:
        List of vendor keys from vendor configuration
    """
    from .vendor_config import get_enabled_vendors
    return get_enabled_vendors()

