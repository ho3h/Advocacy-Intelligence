"""Utility functions for saving scraped references to individual files."""

import os
import json
import re
from urllib.parse import urlparse
from datetime import datetime


def sanitize_filename(name):
    """
    Create a safe filename from a string.
    
    Args:
        name: String to sanitize
        
    Returns:
        Safe filename string
    """
    # Remove or replace invalid filename characters
    name = re.sub(r'[<>:"/\\|?*]', '-', name)
    # Remove leading/trailing spaces and dots
    name = name.strip('. ')
    # Replace multiple spaces/hyphens with single hyphen
    name = re.sub(r'[\s\-]+', '-', name)
    # Limit length
    if len(name) > 100:
        name = name[:100]
    return name


def get_reference_filename(url, customer_name=None):
    """
    Generate a filename for a reference based on URL and customer name.
    
    Args:
        url: Reference URL
        customer_name: Customer name (optional)
        
    Returns:
        Filename string (without extension)
    """
    # Try to extract from URL first (most reliable)
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p]
    
    # Look for case-study or video slug
    filename = None
    if 'case-study' in path_parts:
        idx = path_parts.index('case-study')
        if idx + 1 < len(path_parts):
            filename = path_parts[idx + 1]
    elif 'video' in path_parts:
        idx = path_parts.index('video')
        if idx + 1 < len(path_parts):
            filename = path_parts[idx + 1]
    
    # Fallback to customer name
    if not filename and customer_name:
        filename = customer_name.lower()
    
    # Final fallback: use last part of URL path
    if not filename and path_parts:
        filename = path_parts[-1]
    
    # If still no filename, use timestamp
    if not filename:
        filename = f"reference-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    return sanitize_filename(filename)


def save_reference_file(vendor_name, reference_data, base_dir='data/scraped'):
    """
    Save a single reference to an individual JSON file.
    
    Args:
        vendor_name: Name of the vendor (e.g., "Snowflake")
        reference_data: Dict with reference data (url, customer_name, raw_text, etc.)
        base_dir: Base directory for storing files
        
    Returns:
        Path to saved file, or None if saving failed
    """
    try:
        # Create vendor directory
        vendor_dir = os.path.join(base_dir, vendor_name.lower())
        os.makedirs(vendor_dir, exist_ok=True)
        
        # Generate filename
        filename = get_reference_filename(
            reference_data.get('url', ''),
            reference_data.get('customer_name')
        )
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        full_filename = f"{filename}-{timestamp}.json"
        
        filepath = os.path.join(vendor_dir, full_filename)
        
        # Save reference data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(reference_data, f, indent=2, ensure_ascii=False)
        
        return filepath
        
    except Exception as e:
        print(f"  ⚠ Failed to save reference file: {e}")
        return None

