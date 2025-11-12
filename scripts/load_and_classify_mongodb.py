"""Phase 4: Load MongoDB references to Neo4j and classify them with Gemini."""

import sys
import os
import json
import glob
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from graph.neo4j_client import Neo4jClient
from classifiers.gemini_classifier import ReferenceClassifier


def load_references_from_files(vendor_name='MongoDB'):
    """Load all scraped reference files for a vendor."""
    vendor_dir = os.path.join('data', 'scraped', vendor_name.lower())
    if not os.path.exists(vendor_dir):
        return []
    
    # Find all JSON files (exclude discovered_urls files)
    ref_files = glob.glob(os.path.join(vendor_dir, '*.json'))
    ref_files = [f for f in ref_files if 'discovered_urls' not in f]
    
    references = []
    for filepath in ref_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                ref_data = json.load(f)
                if 'url' in ref_data and 'raw_text' in ref_data:
                    references.append(ref_data)
        except Exception as e:
            print(f"  ⚠ Failed to load {os.path.basename(filepath)}: {e}")
    
    return references


def main():
    """Run Phase 4: Load references to Neo4j and classify them."""
    
    print("=" * 70)
    print("PHASE 4: DATABASE LOADING & CLASSIFICATION (MONGODB)")
    print("=" * 70)
    
    vendor_name = 'MongoDB'
    
    # Initialize components
    print("\n1. Initializing components...")
    db = Neo4jClient()
    classifier = ReferenceClassifier()
    
    # Verify database connection
    if not db.verify_connection():
        print("✗ Failed to connect to Neo4j")
        print("  Check your NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables")
        return
    print("✓ Connected to Neo4j")
    
    # Create indexes
    print("  Creating indexes...")
    db.create_indexes()
    
    # Step 1: Load references from files
    print("\n" + "=" * 70)
    print("STEP 1: LOADING REFERENCES FROM FILES TO NEO4J")
    print("=" * 70)
    
    references = load_references_from_files(vendor_name)
    print(f"📂 Found {len(references)} reference files in data/scraped/mongodb/")
    
    if not references:
        print("✗ No references found. Run Phase 2 scraping first.")
        return
    
    # Load to Neo4j
    loaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Use tqdm if available
    try:
        from tqdm import tqdm
        ref_iterator = tqdm(references, desc="Loading to DB", unit="ref")
        USE_TQDM = True
    except ImportError:
        ref_iterator = references
        USE_TQDM = False
    
    for ref in ref_iterator:
        try:
            ref['vendor_website'] = 'https://www.mongodb.com'
            ref_id = db.load_raw_reference(vendor_name, ref)
            if ref_id:
                loaded_count += 1
                if not USE_TQDM:
                    print(f"✓ Loaded {ref.get('customer_name', 'Unknown')[:50]}...")
            else:
                skipped_count += 1
                if not USE_TQDM:
                    print(f"⚠ Skipped {ref.get('customer_name', 'Unknown')[:50]}... (URL already exists)")
        except Exception as e:
            failed_count += 1
            if not USE_TQDM:
                print(f"✗ Failed to load {ref.get('customer_name', 'Unknown')[:50]}...: {e}")
    
    print(f"\n✓ Loaded {loaded_count}/{len(references)} references to database")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} duplicate URLs (already in database)")
    if failed_count > 0:
        print(f"✗ Failed to load {failed_count} references")
    
    # Step 2: Classify references
    print("\n" + "=" * 70)
    print("STEP 2: CLASSIFYING REFERENCES WITH GEMINI")
    print("=" * 70)
    
    unclassified = db.get_unclassified_references(limit=1000)
    print(f"📋 Found {len(unclassified)} unclassified references")
    
    if len(unclassified) == 0:
        print("✓ All references are already classified!")
        db.close()
        return
    
    print(f"⏱️  Estimated time: {len(unclassified) * 3 / 60:.1f} - {len(unclassified) * 5 / 60:.1f} minutes")
    print(f"💰 Estimated cost: ${len(unclassified) * 0.001:.2f} - ${len(unclassified) * 0.01:.2f}\n")
    
    classified_count = 0
    failed_count = 0
    
    # Use tqdm if available
    try:
        from tqdm import tqdm
        unclassified_iterator = tqdm(enumerate(unclassified, 1), total=len(unclassified), desc="Classifying", unit="ref")
        USE_TQDM = True
    except ImportError:
        unclassified_iterator = enumerate(unclassified, 1)
        USE_TQDM = False
    
    start_time = time.time()
    
    for i, ref in unclassified_iterator:
        if not USE_TQDM:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (len(unclassified) - i) / rate if rate > 0 else 0
            print(f"\n[{i}/{len(unclassified)}] ({i/len(unclassified)*100:.1f}%) | "
                  f"Elapsed: {elapsed/60:.1f}m | "
                  f"ETA: {remaining/60:.1f}m | "
                  f"Success: {classified_count}", flush=True)
            print(f"  📄 Classifying: {ref['url'][:70]}...", flush=True)
        
        try:
            classification = classifier.classify(ref['text'], ref['url'])
            
            if classification:
                db.update_classification(ref['id'], classification)
                classified_count += 1
                if not USE_TQDM:
                    print(f"  ✓ Classified: {classification.get('customer_name', 'Unknown')[:40]} | "
                          f"{classification.get('industry', 'Unknown')} | "
                          f"{', '.join(classification.get('use_cases', [])[:2])}")
            else:
                failed_count += 1
                if not USE_TQDM:
                    print("  ✗ Classification failed (returned None)")
                
        except Exception as e:
            failed_count += 1
            error_msg = str(e)[:100]
            if not USE_TQDM:
                print(f"  ✗ Error: {error_msg}")
            elif i % 10 == 0:  # Show errors every 10 items when using tqdm
                import sys
                print(f"\n✗ [{i}/{len(unclassified)}] Error: {error_msg}", file=sys.stderr, flush=True)
        
        # Small delay to avoid rate limits
        if i < len(unclassified):
            time.sleep(0.5)
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("CLASSIFICATION SUMMARY")
    print("=" * 70)
    print(f"✓ Successfully classified: {classified_count}/{len(unclassified)} references")
    if failed_count > 0:
        print(f"✗ Failed to classify: {failed_count} references")
    print(f"⏱️  Total time: {elapsed_time/60:.1f} minutes ({elapsed_time:.0f} seconds)")
    if classified_count > 0:
        print(f"📊 Average time per classification: {elapsed_time/classified_count:.1f} seconds")
    
    # Step 3: Show final stats
    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\n" + "=" * 70)
    print("✓ Phase 4 complete!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"  • Loaded: {loaded_count} references to Neo4j")
    print(f"  • Classified: {classified_count} references")
    print(f"  • Total references in database: {stats.get('total_references', 'N/A')}")
    print(f"  • Total customers: {stats.get('total_customers', 'N/A')}")
    print(f"\n💡 Next steps:")
    print(f"  1. Open Neo4j Browser to inspect the data")
    print(f"  2. Run sample queries to test similarity search")
    print(f"  3. Manually QA 10-20 classifications for accuracy")
    
    db.close()


if __name__ == '__main__':
    main()

