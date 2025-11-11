"""Cleanup script to remove duplicate references from Neo4j database."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from graph.neo4j_client import Neo4jClient


def cleanup_duplicates():
    """Remove duplicate references (same URL, multiple Reference nodes)."""
    
    print("=" * 60)
    print("CLEANUP: Removing Duplicate References")
    print("=" * 60)
    
    db = Neo4jClient()
    
    if not db.verify_connection():
        print("✗ Failed to connect to Neo4j")
        return
    
    print("✓ Connected to Neo4j")
    
    with db.driver.session() as session:
        # Find duplicate URLs
        print("\n1. Finding duplicate references...")
        result = session.run("""
            MATCH (r:Reference)
            WITH r.url as url, collect(r) as refs
            WHERE size(refs) > 1
            RETURN url, size(refs) as count, 
                   [r in refs | r.id] as ref_ids,
                   [r in refs | r.classified] as classified_flags
            ORDER BY count DESC
        """)
        
        duplicates = list(result)
        
        if not duplicates:
            print("✓ No duplicates found!")
            db.close()
            return
        
        print(f"Found {len(duplicates)} URLs with duplicates")
        
        # Show summary
        total_duplicates = sum(d['count'] - 1 for d in duplicates)
        print(f"Total duplicate references to remove: {total_duplicates}")
        
        # Process each duplicate
        removed_count = 0
        kept_count = 0
        
        print("\n2. Removing duplicates (keeping the first classified one, or first if none classified)...")
        
        for dup in duplicates:
            url = dup['url']
            ref_ids = dup['ref_ids']
            classified_flags = dup['classified_flags']
            
            # Strategy: Keep the first classified reference, or first if none are classified
            keep_idx = 0
            for i, is_classified in enumerate(classified_flags):
                if is_classified:
                    keep_idx = i
                    break
            
            keep_id = ref_ids[keep_idx]
            remove_ids = [rid for i, rid in enumerate(ref_ids) if i != keep_idx]
            
            print(f"\n  URL: {url[:60]}...")
            print(f"    Keeping: {keep_id} (classified: {classified_flags[keep_idx]})")
            print(f"    Removing: {len(remove_ids)} duplicate(s)")
            
            # Delete duplicate references and their relationships
            for remove_id in remove_ids:
                session.run("""
                    MATCH (r:Reference {id: $ref_id})
                    DETACH DELETE r
                """, {'ref_id': remove_id})
                removed_count += 1
            
            kept_count += 1
        
        print(f"\n✓ Cleanup complete!")
        print(f"  Kept: {kept_count} references")
        print(f"  Removed: {removed_count} duplicates")
        
        # Show final stats
        print("\n3. Final statistics:")
        stats = db.get_stats()
        for key, value in stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    db.close()


def cleanup_bad_urls():
    """Remove references that point to listing pages (not actual case studies)."""
    
    print("\n" + "=" * 60)
    print("CLEANUP: Removing Bad URLs (Listing Pages)")
    print("=" * 60)
    
    db = Neo4jClient()
    
    if not db.verify_connection():
        print("✗ Failed to connect to Neo4j")
        return
    
    with db.driver.session() as session:
        # Find bad URLs (listing pages, not case studies)
        print("\n1. Finding references with bad URLs...")
        result = session.run("""
            MATCH (r:Reference)
            WHERE (r.url CONTAINS '/en/customers/all-customers/' 
                   OR r.url CONTAINS '/customers/all-customers/')
              AND NOT r.url CONTAINS '/case-study/'
              AND NOT r.url CONTAINS '/video/'
            RETURN r.id as ref_id, r.url as url, r.word_count as word_count
        """)
        
        bad_refs = list(result)
        
        if not bad_refs:
            print("✓ No bad URLs found!")
            db.close()
            return
        
        print(f"Found {len(bad_refs)} references with bad URLs")
        
        # Show what will be removed
        print("\n2. References to remove:")
        for ref in bad_refs:
            print(f"  - {ref['url']} (ID: {ref['ref_id']}, {ref['word_count']} words)")
        
        # Remove bad references
        print("\n3. Removing bad references...")
        removed_count = 0
        
        for ref in bad_refs:
            session.run("""
                MATCH (r:Reference {id: $ref_id})
                DETACH DELETE r
            """, {'ref_id': ref['ref_id']})
            removed_count += 1
        
        print(f"\n✓ Removed {removed_count} bad references")
        
        # Show final stats
        print("\n4. Final statistics:")
        stats = db.get_stats()
        for key, value in stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")
    
    db.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup duplicate references and bad URLs')
    parser.add_argument('--duplicates', action='store_true', help='Remove duplicate references')
    parser.add_argument('--bad-urls', action='store_true', help='Remove bad URLs (listing pages)')
    parser.add_argument('--all', action='store_true', help='Run all cleanup tasks')
    
    args = parser.parse_args()
    
    if args.all or args.duplicates:
        cleanup_duplicates()
    
    if args.all or args.bad_urls:
        cleanup_bad_urls()
    
    if not (args.duplicates or args.bad_urls or args.all):
        print("No cleanup tasks specified. Use --duplicates, --bad-urls, or --all")
        print("\nExample:")
        print("  python scripts/cleanup_duplicates.py --all")

