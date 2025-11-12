"""Sample queries to explore MongoDB customer reference data in Neo4j."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from graph.neo4j_client import Neo4jClient


def main():
    """Run sample queries on MongoDB data."""
    
    print("=" * 70)
    print("MONGODB CUSTOMER REFERENCE DATA - SAMPLE QUERIES")
    print("=" * 70)
    
    db = Neo4jClient()
    
    if not db.verify_connection():
        print("✗ Failed to connect to Neo4j")
        return
    
    print("✓ Connected to Neo4j\n")
    
    # Query 1: Count references by vendor
    print("=" * 70)
    print("QUERY 1: References by Vendor")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor)-[:PUBLISHED]->(r:Reference)
        RETURN v.name as vendor, count(r) as ref_count
        ORDER BY ref_count DESC
    """)
    for record in result:
        print(f"  {record['vendor']}: {record['ref_count']} references")
    
    # Query 2: Top industries
    print("\n" + "=" * 70)
    print("QUERY 2: Top Industries (MongoDB)")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)
        MATCH (r)-[:FEATURES]->(c:Customer)-[:IN_INDUSTRY]->(i:Industry)
        RETURN i.name as industry, count(DISTINCT c) as customer_count
        ORDER BY customer_count DESC
        LIMIT 10
    """)
    for record in result:
        print(f"  {record['industry']}: {record['customer_count']} customers")
    
    # Query 3: Top use cases
    print("\n" + "=" * 70)
    print("QUERY 3: Top Use Cases (MongoDB)")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)
        MATCH (r)-[:ADDRESSES_USE_CASE]->(uc:UseCase)
        RETURN uc.name as use_case, count(r) as ref_count
        ORDER BY ref_count DESC
        LIMIT 10
    """)
    for record in result:
        print(f"  {record['use_case']}: {record['ref_count']} references")
    
    # Query 4: Company sizes
    print("\n" + "=" * 70)
    print("QUERY 4: Company Size Distribution (MongoDB)")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)
        MATCH (r)-[:FEATURES]->(c:Customer)
        RETURN c.size as size, count(DISTINCT c) as customer_count
        ORDER BY customer_count DESC
    """)
    for record in result:
        size = record['size'] or 'Unknown'
        print(f"  {size}: {record['customer_count']} customers")
    
    # Query 5: Regions
    print("\n" + "=" * 70)
    print("QUERY 5: Regional Distribution (MongoDB)")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)
        MATCH (r)-[:FEATURES]->(c:Customer)
        RETURN c.region as region, count(DISTINCT c) as customer_count
        ORDER BY customer_count DESC
    """)
    for record in result:
        region = record['region'] or 'Unknown'
        print(f"  {region}: {record['customer_count']} customers")
    
    # Query 6: Sample customers with use cases
    print("\n" + "=" * 70)
    print("QUERY 6: Sample Customers with Use Cases (MongoDB)")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)
        MATCH (r)-[:FEATURES]->(c:Customer)
        MATCH (r)-[:ADDRESSES_USE_CASE]->(uc:UseCase)
        WITH c, collect(DISTINCT uc.name) as use_cases
        RETURN c.name as customer, c.industry as industry, use_cases
        ORDER BY size(use_cases) DESC
        LIMIT 10
    """)
    for record in result:
        customer = record['customer'] or 'Unknown'
        industry = record['industry'] or 'Unknown'
        use_cases = ', '.join(record['use_cases'][:3])
        print(f"  {customer} ({industry})")
        print(f"    Use cases: {use_cases}")
    
    # Query 7: Outcomes with metrics
    print("\n" + "=" * 70)
    print("QUERY 7: Sample Outcomes with Metrics (MongoDB)")
    print("=" * 70)
    result = db.driver.session().run("""
        MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)
        MATCH (r)-[:FEATURES]->(c:Customer)
        MATCH (r)-[:ACHIEVED_OUTCOME]->(o:Outcome)
        WHERE o.metric IS NOT NULL AND o.metric <> ''
        RETURN c.name as customer, o.type as outcome_type, 
               o.description as description, o.metric as metric
        LIMIT 10
    """)
    for record in result:
        customer = record['customer'] or 'Unknown'
        outcome_type = record['outcome_type'] or 'Unknown'
        metric = record['metric'] or 'N/A'
        description = (record['description'] or '')[:60]
        print(f"  {customer}: {outcome_type}")
        print(f"    {description}")
        print(f"    Metric: {metric}")
    
    print("\n" + "=" * 70)
    print("✓ Query complete!")
    print("=" * 70)
    print("\n💡 Try these queries in Neo4j Browser:")
    print("  1. MATCH (v:Vendor {name: 'MongoDB'})-[:PUBLISHED]->(r:Reference)")
    print("     RETURN count(r) as total_references")
    print("\n  2. MATCH (c:Customer)<-[:FEATURES]-(r:Reference)<-[:PUBLISHED]-(v:Vendor {name: 'MongoDB'})")
    print("     MATCH (c)-[:IN_INDUSTRY]->(i:Industry)")
    print("     RETURN i.name, count(DISTINCT c) ORDER BY count(DISTINCT c) DESC")
    
    db.close()


if __name__ == '__main__':
    main()

