"""Load and validate vendor configurations from JSON file."""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path


def get_vendors_config_path() -> Path:
    """Get path to vendors.json config file."""
    # Get project root (assume this file is in src/pipeline/)
    project_root = Path(__file__).parent.parent.parent
    return project_root / 'data' / 'vendors.json'


def load_vendor_configs() -> Dict[str, Dict]:
    """
    Load vendor configurations from data/vendors.json.
    
    Returns:
        Dictionary mapping vendor keys to their configurations
        
    Raises:
        FileNotFoundError: If vendors.json doesn't exist
        ValueError: If JSON is invalid or missing required fields
    """
    config_path = get_vendors_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Vendor config file not found: {config_path}\n"
            f"Create data/vendors.json with vendor configurations."
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)
    
    # Validate each vendor config
    required_fields = ['name', 'website', 'discovery_method', 'scraper_class']
    for vendor_key, vendor_config in configs.items():
        for field in required_fields:
            if field not in vendor_config:
                raise ValueError(
                    f"Vendor '{vendor_key}' missing required field: {field}"
                )
        
        # Validate discovery_method
        if vendor_config['discovery_method'] not in ['sitemap', 'pagination']:
            raise ValueError(
                f"Vendor '{vendor_key}' has invalid discovery_method: "
                f"{vendor_config['discovery_method']}. Must be 'sitemap' or 'pagination'"
            )
        
        # Validate error_handling config (optional, but if present must have required fields)
        if 'error_handling' in vendor_config:
            error_config = vendor_config['error_handling']
            if 'retry_on_failure' not in error_config:
                error_config['retry_on_failure'] = True
            if 'max_retries' not in error_config:
                error_config['max_retries'] = 3
            if 'skip_on_error' not in error_config:
                error_config['skip_on_error'] = False
    
    return configs


def get_vendor_config(vendor_key: str) -> Optional[Dict]:
    """
    Get configuration for a specific vendor.
    
    Args:
        vendor_key: Vendor key (e.g., 'mongodb', 'snowflake')
        
    Returns:
        Vendor configuration dict, or None if not found
    """
    configs = load_vendor_configs()
    return configs.get(vendor_key.lower())


def get_enabled_vendors() -> List[str]:
    """
    Get list of enabled vendor keys.
    
    Returns:
        List of vendor keys that have enabled=true
    """
    configs = load_vendor_configs()
    return [
        key for key, config in configs.items()
        if config.get('enabled', True)
    ]


def validate_vendor_key(vendor_key: str) -> bool:
    """
    Check if a vendor key exists in configuration.
    
    Args:
        vendor_key: Vendor key to check
        
    Returns:
        True if vendor exists, False otherwise
    """
    configs = load_vendor_configs()
    return vendor_key.lower() in configs

