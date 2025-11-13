"""Test the full pipeline using the unified pipeline system.

This is a legacy test script. For new testing, use:
    python scripts/run_pipeline.py --vendors snowflake --phases 2,3,4
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pipeline.runner import PipelineRunner
from pipeline.vendor_config import validate_vendor_key, get_enabled_vendors


def main():
    """Run the test pipeline using unified pipeline system."""
    
    print("=" * 60)
    print("CUSTOMER REFERENCE INTELLIGENCE - TEST PIPELINE")
    print("=" * 60)
    print("\n⚠️  This is a legacy test script.")
    print("For new testing, use: python scripts/run_pipeline.py --vendors snowflake")
    print("=" * 60)
    
    # Use unified pipeline
    vendor_key = "snowflake"
    
    if not validate_vendor_key(vendor_key):
        print(f"✗ Vendor '{vendor_key}' not found in configuration")
        print("Available vendors:", ', '.join(get_enabled_vendors()))
        return
    
    print(f"\nRunning pipeline for: {vendor_key}")
    print("Phases: 2,3,4 (scraping, loading, classification)")
    
    runner = PipelineRunner()
    result = runner.run_vendor(
        vendor_key=vendor_key,
        phases=[2, 3, 4],
        dry_run=False,
        force=False
    )
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Result: {result}")
    print("\nNext steps:")
    print("1. Open Neo4j Browser to inspect data")
    print("2. Run sample queries to test similarity search")
    print("3. Manually QA 10-20 classifications for accuracy")


if __name__ == '__main__':
    main()
