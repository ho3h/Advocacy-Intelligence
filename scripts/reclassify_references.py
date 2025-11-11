"""Re-run classification on existing references in Neo4j.

Useful when:
- Improving classification prompts
- Expanding schema (new fields/relationships)
- Fixing classification errors
- Re-processing after taxonomy updates
"""

import sys
import os
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from graph.neo4j_client import Neo4jClient
from classifiers.gemini_classifier import ReferenceClassifier


def mark_unclassified(db, vendor=None, url_pattern=None, all_refs=False):
    """
    Mark references as unclassified (ready for re-classification).
    
    Args:
        db: Neo4jClient instance
        vendor: Optional vendor name to filter by
        url_pattern: Optional URL pattern to filter by (e.g., 'snowflake.com')
        all_refs: If True, mark ALL references as unclassified
    """
    with db.driver.session() as session:
        if all_refs:
            # Mark all references
            result = session.run("""
                MATCH (r:Reference)
                SET r.classified = false
                RETURN count(r) as count
            """)
            count = result.single()['count']
            print(f"✓ Marked {count} references as unclassified")
            return count
        
        # Build query with filters
        query = "MATCH (r:Reference)"
        conditions = []
        params = {}
        
        if vendor:
            query += "-[:PUBLISHED]->(v:Vendor {name: $vendor})"
            params['vendor'] = vendor
            conditions.append("r.classified = true")
        
        if url_pattern:
            conditions.append("r.url CONTAINS $url_pattern")
            params['url_pattern'] = url_pattern
        
        if not conditions:
            conditions.append("r.classified = true")
        
        query += f"\nWHERE {' AND '.join(conditions)}"
        query += "\nSET r.classified = false"
        query += "\nRETURN count(r) as count"
        
        result = session.run(query, params)
        count = result.single()['count']
        print(f"✓ Marked {count} references as unclassified")
        return count


def cleanup_old_classifications(db, vendor=None, url_pattern=None, all_refs=False):
    """
    Remove old classification relationships before re-classifying.
    
    This is useful when schema changes - removes old relationships
    so new classification can create fresh ones.
    
    Args:
        db: Neo4jClient instance
        vendor: Optional vendor name to filter by
        url_pattern: Optional URL pattern to filter by
        all_refs: If True, clean up ALL references
    """
    with db.driver.session() as session:
        # Build query to find references
        query = "MATCH (r:Reference)"
        conditions = []
        params = {}
        
        if vendor:
            query += "-[:PUBLISHED]->(v:Vendor {name: $vendor})"
            params['vendor'] = vendor
        
        if url_pattern:
            conditions.append("r.url CONTAINS $url_pattern")
            params['url_pattern'] = url_pattern
        
        if not all_refs:
            conditions.append("r.classified = false")
        
        if conditions:
            query += f"\nWHERE {' AND '.join(conditions)}"
        
        # Delete all classification relationships
        query += """
        WITH r
        OPTIONAL MATCH (r)-[rel1:FEATURES]->(c:Customer)
        OPTIONAL MATCH (c)-[rel2:IN_INDUSTRY]->(i:Industry)
        OPTIONAL MATCH (r)-[rel3:ADDRESSES_USE_CASE]->(uc:UseCase)
        OPTIONAL MATCH (r)-[rel4:ACHIEVED_OUTCOME]->(o:Outcome)
        OPTIONAL MATCH (r)-[rel5:MENTIONS_PERSONA]->(p:Persona)
        OPTIONAL MATCH (r)-[rel6:MENTIONS_TECH]->(t:Technology)
        
        DELETE rel1, rel2, rel3, rel4, rel5, rel6
        
        WITH r, c
        WHERE c IS NOT NULL AND NOT (c)<-[:FEATURES]-()
        DELETE c
        
        RETURN count(r) as count
        """
        
        result = session.run(query, params)
        count = result.single()['count']
        print(f"✓ Cleaned up old classifications for {count} references")
        return count


def reclassify(db, classifier, vendor=None, url_pattern=None, limit=None, cleanup=False):
    """
    Re-run classification on unclassified references.
    
    Args:
        db: Neo4jClient instance
        classifier: ReferenceClassifier instance
        vendor: Optional vendor name to filter by
        url_pattern: Optional URL pattern to filter by
        limit: Max number of references to classify
        cleanup: If True, remove old relationships first
    """
    # Get unclassified references
    with db.driver.session() as session:
        query = "MATCH (r:Reference)"
        conditions = ["r.classified = false"]
        params = {}
        
        if vendor:
            query += "-[:PUBLISHED]->(v:Vendor {name: $vendor})"
            params['vendor'] = vendor
            query += "\nMATCH (r)"
        
        if url_pattern:
            conditions.append("r.url CONTAINS $url_pattern")
            params['url_pattern'] = url_pattern
        
        query += f"\nWHERE {' AND '.join(conditions)}"
        query += "\nRETURN r.id as id, r.raw_text as text, r.url as url"
        
        if limit:
            query += "\nLIMIT $limit"
            params['limit'] = limit
        
        result = session.run(query, params)
        references = [dict(record) for record in result]
    
    if not references:
        print("No unclassified references found")
        return
    
    print(f"\nFound {len(references)} references to classify")
    
    # Cleanup old relationships if requested
    if cleanup:
        print("\nCleaning up old classification relationships...")
        ref_ids = [r['id'] for r in references]
        with db.driver.session() as session:
            for ref_id in ref_ids:
                session.run("""
                    MATCH (r:Reference {id: $ref_id})
                    OPTIONAL MATCH (r)-[rel1:FEATURES]->(c:Customer)
                    OPTIONAL MATCH (c)-[rel2:IN_INDUSTRY]->(i:Industry)
                    OPTIONAL MATCH (r)-[rel3:ADDRESSES_USE_CASE]->(uc:UseCase)
                    OPTIONAL MATCH (r)-[rel4:ACHIEVED_OUTCOME]->(o:Outcome)
                    OPTIONAL MATCH (r)-[rel5:MENTIONS_PERSONA]->(p:Persona)
                    OPTIONAL MATCH (r)-[rel6:MENTIONS_TECH]->(t:Technology)
                    
                    DELETE rel1, rel2, rel3, rel4, rel5, rel6
                    
                    WITH r, c
                    WHERE c IS NOT NULL AND NOT (c)<-[:FEATURES]-()
                    DELETE c
                """, {'ref_id': ref_id})
        print("✓ Cleanup complete")
    
    # Classify references
    print("\nRe-classifying references...")
    classified_count = 0
    failed_count = 0
    
    for i, ref in enumerate(references, 1):
        print(f"\n[{i}/{len(references)}] Classifying {ref['url'][:60]}...")
        
        try:
            classification = classifier.classify(ref['text'], ref['url'])
            
            if classification:
                db.update_classification(ref['id'], classification)
                classified_count += 1
                print(f"✓ Classified: {classification.get('customer_name')} | "
                      f"{classification.get('industry')} | "
                      f"{', '.join(classification.get('use_cases', [])[:2])}")
            else:
                failed_count += 1
                print("✗ Classification failed")
                
        except Exception as e:
            failed_count += 1
            print(f"✗ Error: {e}")
    
    print(f"\n✓ Successfully classified {classified_count}/{len(references)} references")
    if failed_count > 0:
        print(f"⚠ Failed to classify {failed_count} references")


def main():
    parser = argparse.ArgumentParser(
        description='Re-run classification on existing references',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mark all Snowflake references for re-classification
  python scripts/reclassify_references.py --mark-unclassified --vendor Snowflake
  
  # Clean up old classifications and re-classify all references
  python scripts/reclassify_references.py --reclassify --cleanup --all
  
  # Re-classify specific references matching URL pattern
  python scripts/reclassify_references.py --reclassify --url-pattern "snowflake.com" --limit 10
  
  # Mark all references as unclassified (for full re-run)
  python scripts/reclassify_references.py --mark-unclassified --all
        """
    )
    
    parser.add_argument('--mark-unclassified', action='store_true',
                       help='Mark references as unclassified (ready for re-classification)')
    parser.add_argument('--reclassify', action='store_true',
                       help='Re-run classification on unclassified references')
    parser.add_argument('--cleanup', action='store_true',
                       help='Remove old classification relationships before re-classifying')
    parser.add_argument('--vendor', type=str,
                       help='Filter by vendor name (e.g., Snowflake)')
    parser.add_argument('--url-pattern', type=str,
                       help='Filter by URL pattern (e.g., snowflake.com)')
    parser.add_argument('--all', action='store_true',
                       help='Apply to all references (use with caution)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of references to process')
    
    args = parser.parse_args()
    
    if not (args.mark_unclassified or args.reclassify):
        parser.print_help()
        return
    
    # Initialize components
    print("Initializing...")
    db = Neo4jClient()
    
    if not db.verify_connection():
        print("✗ Failed to connect to Neo4j")
        return
    
    print("✓ Connected to Neo4j")
    
    # Mark as unclassified
    if args.mark_unclassified:
        print("\nMarking references as unclassified...")
        mark_unclassified(db, vendor=args.vendor, url_pattern=args.url_pattern, all_refs=args.all)
    
    # Re-classify
    if args.reclassify:
        classifier = ReferenceClassifier()
        reclassify(
            db, classifier,
            vendor=args.vendor,
            url_pattern=args.url_pattern,
            limit=args.limit,
            cleanup=args.cleanup
        )
    
    # Show stats
    print("\nFinal Statistics:")
    print("=" * 60)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    db.close()


if __name__ == '__main__':
    main()

