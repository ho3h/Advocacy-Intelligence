#!/usr/bin/env python3
"""Unified pipeline runner for processing all vendors through all phases.

Usage:
    # Process all vendors
    python scripts/run_pipeline.py

    # Process specific vendors
    python scripts/run_pipeline.py --vendors mongodb,snowflake

    # Run specific phases only
    python scripts/run_pipeline.py --vendors mongodb --phases 1,2

    # Skip phases
    python scripts/run_pipeline.py --vendors mongodb --skip-phases 1

    # Dry run (show what would be processed)
    python scripts/run_pipeline.py --dry-run

    # Force re-processing (skip idempotency checks)
    python scripts/run_pipeline.py --force
"""

import sys
import argparse
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pipeline.runner import PipelineRunner
from pipeline.vendor_config import get_enabled_vendors, validate_vendor_key
from pipeline.reporting import PipelineReporter


def parse_phases(phases_str: str) -> list:
    """Parse comma-separated phase numbers."""
    if not phases_str:
        return None
    
    try:
        phases = [int(p.strip()) for p in phases_str.split(',')]
        # Validate phase numbers
        for p in phases:
            if p < 1 or p > 4:
                raise ValueError(f"Invalid phase number: {p}. Must be 1-4")
        return phases
    except ValueError as e:
        print(f"Error parsing phases: {e}")
        sys.exit(1)


def parse_vendors(vendors_str: str) -> list:
    """Parse comma-separated vendor keys."""
    if not vendors_str:
        return None
    
    vendors = [v.strip().lower() for v in vendors_str.split(',')]
    
    # Validate vendor keys
    for vendor in vendors:
        if not validate_vendor_key(vendor):
            enabled = get_enabled_vendors()
            print(f"Error: Unknown vendor '{vendor}'")
            print(f"Available vendors: {', '.join(enabled)}")
            sys.exit(1)
    
    return vendors


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Unified pipeline runner for processing vendors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--vendors',
        type=str,
        help='Comma-separated vendor keys (e.g., mongodb,snowflake). Default: all enabled vendors'
    )
    
    parser.add_argument(
        '--phases',
        type=str,
        help='Comma-separated phase numbers 1-4 (e.g., 1,2,3). Default: all phases'
    )
    
    parser.add_argument(
        '--skip-phases',
        type=str,
        help='Comma-separated phase numbers to skip (e.g., 1,4)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without executing'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip idempotency checks (re-process everything)'
    )
    
    args = parser.parse_args()
    
    # Parse arguments
    vendor_keys = parse_vendors(args.vendors)
    phases = parse_phases(args.phases)
    skip_phases = parse_phases(args.skip_phases)
    
    # Print configuration
    print("="*70)
    print("UNIFIED PIPELINE RUNNER")
    print("="*70)
    
    if args.dry_run:
        print("\n⚠ DRY RUN MODE - No changes will be made\n")
    
    if args.force:
        print("\n⚠ FORCE MODE - Idempotency checks disabled\n")
    
    if vendor_keys:
        print(f"Vendors: {', '.join(vendor_keys)}")
    else:
        enabled = get_enabled_vendors()
        print(f"Vendors: All enabled ({', '.join(enabled)})")
    
    if phases:
        print(f"Phases: {', '.join(map(str, phases))}")
    else:
        print("Phases: All (1, 2, 3, 4)")
    
    if skip_phases:
        print(f"Skip phases: {', '.join(map(str, skip_phases))}")
    
    print("="*70 + "\n")
    
    # Initialize pipeline runner
    try:
        runner = PipelineRunner()
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        sys.exit(1)
    
    # Run pipeline
    try:
        results = runner.run_all_vendors(
            vendor_keys=vendor_keys,
            phases=phases,
            skip_phases=skip_phases,
            force=args.force,
            dry_run=args.dry_run
        )
        
        # Generate and save report
        summary = runner.reporter.generate_summary(results)
        runner.reporter.save_report(summary)
        runner.reporter.save_error_log()
        runner.reporter.print_summary_table(summary)
        
        # Exit with error code if there were errors
        if summary['errors'] > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Pipeline interrupted by user")
        runner.reporter.save_error_log()
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        runner.reporter.log_error(str(e))
        runner.reporter.save_error_log()
        sys.exit(1)
    finally:
        runner.db.close()


if __name__ == '__main__':
    main()

