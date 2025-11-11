"""Test the full pipeline: scrape Snowflake → load to Neo4j → classify."""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.snowflake_scraper import SnowflakeScraper
from graph.neo4j_client import Neo4jClient
from classifiers.gemini_classifier import ReferenceClassifier
from utils.file_storage import save_reference_file


def main():
    """Run the test pipeline."""
    
    print("=" * 60)
    print("CUSTOMER REFERENCE INTELLIGENCE - TEST PIPELINE")
    print("=" * 60)
    
    # Initialize components
    print("\n1. Initializing components...")
    scraper = SnowflakeScraper(delay=2)
    db = Neo4jClient()
    classifier = ReferenceClassifier()
    
    # Verify database connection
    if not db.verify_connection():
        print("✗ Failed to connect to Neo4j")
        return
    print("✓ Connected to Neo4j")
    
    # Create indexes
    db.create_indexes()
    
    # Step 1: Scrape Snowflake
    print("\n2. Scraping Snowflake customer references...")
    references = scraper.scrape_all()
    
    if not references:
        print("✗ No references scraped")
        return
    
    print(f"✓ Scraped {len(references)} references")
    
    # Step 2: Save individual reference files and load to Neo4j
    print("\n3. Saving reference files and loading to Neo4j...")
    save_files = os.getenv('SAVE_RAW_DATA', 'true').lower() == 'true'  # Default to true now
    loaded_count = 0
    skipped_count = 0
    saved_count = 0
    
    vendor_name = 'Snowflake'
    
    for ref in references:
        # Save individual reference file (organized by vendor)
        if save_files:
            filepath = save_reference_file(vendor_name, ref)
            if filepath:
                saved_count += 1
        
        # Load to Neo4j
        try:
            ref['vendor_website'] = 'https://www.snowflake.com'
            ref_id = db.load_raw_reference(vendor_name, ref)
            if ref_id:
                loaded_count += 1
                print(f"✓ Loaded {ref['customer_name']} (ID: {ref_id})")
            else:
                skipped_count += 1
                print(f"⚠ Skipped {ref['customer_name']} (URL already exists)")
        except Exception as e:
            print(f"✗ Failed to load {ref.get('customer_name', 'Unknown')}: {e}")
    
    print(f"\n✓ Loaded {loaded_count}/{len(references)} references to database")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} duplicate URLs")
    if save_files:
        print(f"✓ Saved {saved_count} reference files to data/scraped/{vendor_name.lower()}/")
    
    # Step 3: Classify references
    print("\n4. Classifying references with Gemini...")
    
    unclassified = db.get_unclassified_references(limit=100)
    print(f"Found {len(unclassified)} unclassified references")
    
    classified_count = 0
    failed_count = 0
    
    for i, ref in enumerate(unclassified, 1):
        print(f"\n[{i}/{len(unclassified)}] Classifying {ref['url'][:60]}...")
        print(f"    Text length: {len(ref['text'])} chars")
        
        try:
            classification = classifier.classify(ref['text'], ref['url'])
            
            if classification:
                db.update_classification(ref['id'], classification)
                classified_count += 1
                print(f"✓ Classified as: {classification.get('customer_name')} | "
                      f"{classification.get('industry')} | "
                      f"{', '.join(classification.get('use_cases', [])[:2])}")
            else:
                failed_count += 1
                print("✗ Classification failed")
                
        except Exception as e:
            failed_count += 1
            print(f"✗ Error: {e}")
    
    print(f"\n✓ Successfully classified {classified_count}/{len(unclassified)} references")
    if failed_count > 0:
        print(f"⚠ Failed to classify {failed_count} references")
    
    # Step 4: Show stats
    print("\n5. Final Statistics:")
    print("=" * 60)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\n✓ Pipeline complete!")
    print("\nNext steps:")
    print("1. Open Neo4j Browser to inspect data")
    print("2. Run sample queries to test similarity search")
    print("3. Manually QA 10-20 classifications for accuracy")
    
    db.close()


if __name__ == '__main__':
    main()

