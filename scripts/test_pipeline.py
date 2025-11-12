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
    print("\n" + "=" * 60)
    print("STEP 2: SCRAPING SNOWFLAKE CUSTOMER REFERENCES")
    print("=" * 60)
    references = scraper.scrape_all()
    
    if not references:
        print("✗ No references scraped")
        return
    
    print(f"✓ Scraped {len(references)} references")
    
    # Step 2: Save individual reference files and load to Neo4j
    print("\n" + "=" * 60)
    print("STEP 3: SAVING FILES AND LOADING TO NEO4J")
    print("=" * 60)
    save_files = os.getenv('SAVE_RAW_DATA', 'true').lower() == 'true'  # Default to true now
    loaded_count = 0
    skipped_count = 0
    saved_count = 0
    
    vendor_name = 'Snowflake'
    
    # Use tqdm if available for progress bar
    try:
        from tqdm import tqdm
        ref_iterator = tqdm(references, desc="Loading to DB", unit="ref")
    except ImportError:
        ref_iterator = references
    
    for ref in ref_iterator:
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
                if 'tqdm' not in str(type(ref_iterator)):
                    print(f"✓ Loaded {ref['customer_name']} (ID: {ref_id})")
            else:
                skipped_count += 1
                if 'tqdm' not in str(type(ref_iterator)):
                    print(f"⚠ Skipped {ref['customer_name']} (URL already exists)")
        except Exception as e:
            if 'tqdm' not in str(type(ref_iterator)):
                print(f"✗ Failed to load {ref.get('customer_name', 'Unknown')}: {e}")
    
    print(f"\n✓ Loaded {loaded_count}/{len(references)} references to database")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} duplicate URLs")
    if save_files:
        print(f"✓ Saved {saved_count} reference files to data/scraped/{vendor_name.lower()}/")
    
    # Step 3: Classify references
    print("\n" + "=" * 60)
    print("STEP 4: CLASSIFYING REFERENCES WITH GEMINI")
    print("=" * 60)
    
    unclassified = db.get_unclassified_references(limit=1000)  # Increased limit
    print(f"📋 Found {len(unclassified)} unclassified references")
    
    if len(unclassified) > 0:
        print(f"⏱️  Estimated time: {len(unclassified) * 3 / 60:.1f} - {len(unclassified) * 5 / 60:.1f} minutes")
        print(f"💰 Estimated cost: ${len(unclassified) * 0.001:.2f} - ${len(unclassified) * 0.01:.2f}\n")
    
    classified_count = 0
    failed_count = 0
    
    # Use tqdm if available
    try:
        from tqdm import tqdm
        unclassified_iterator = tqdm(enumerate(unclassified, 1), total=len(unclassified), desc="Classifying", unit="ref")
    except ImportError:
        unclassified_iterator = enumerate(unclassified, 1)
    
    for i, ref in unclassified_iterator:
        if 'tqdm' not in str(type(unclassified_iterator)):
            print(f"\n[{i}/{len(unclassified)}] Classifying {ref['url'][:60]}...")
            print(f"    Text length: {len(ref['text'])} chars")
        
        try:
            classification = classifier.classify(ref['text'], ref['url'])
            
            if classification:
                db.update_classification(ref['id'], classification)
                classified_count += 1
                if 'tqdm' not in str(type(unclassified_iterator)):
                    print(f"✓ Classified as: {classification.get('customer_name')} | "
                          f"{classification.get('industry')} | "
                          f"{', '.join(classification.get('use_cases', [])[:2])}")
            else:
                failed_count += 1
                if 'tqdm' not in str(type(unclassified_iterator)):
                    print("✗ Classification failed")
                
        except Exception as e:
            failed_count += 1
            if 'tqdm' not in str(type(unclassified_iterator)):
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

