"""Neo4j database client for customer reference intelligence."""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()


class Neo4jClient:
    """Client for interacting with Neo4j AuraDB."""
    
    def __init__(self):
        """Initialize connection to Neo4j."""
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME')
        self.password = os.getenv('NEO4J_PASSWORD')
        
        if not all([self.uri, self.username, self.password]):
            raise ValueError("Missing Neo4j credentials in environment variables")
        
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )
    
    def close(self):
        """Close database connection."""
        self.driver.close()
    
    def verify_connection(self):
        """Test database connection."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                return record["test"] == 1
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def create_indexes(self):
        """Create database indexes for performance."""
        with self.driver.session() as session:
            # Customer name index
            session.run("""
                CREATE INDEX customer_name IF NOT EXISTS 
                FOR (c:Customer) ON (c.name)
            """)
            
            # Reference URL index
            session.run("""
                CREATE INDEX reference_url IF NOT EXISTS 
                FOR (r:Reference) ON (r.url)
            """)
            
            # Vendor name index
            session.run("""
                CREATE INDEX vendor_name IF NOT EXISTS 
                FOR (v:Vendor) ON (v.name)
            """)
            
            print("✓ Indexes created")
    
    def load_raw_reference(self, vendor_name, reference_data):
        """
        Load raw scraped reference into database.
        Skips if URL already exists (deduplication).
        
        Args:
            vendor_name: Name of vendor who published reference
            reference_data: Dict with keys: url, raw_text, scraped_date, word_count
            
        Returns:
            Created reference ID, or None if URL already exists
        """
        with self.driver.session() as session:
            # Check if URL already exists
            existing = session.run("""
                MATCH (r:Reference {url: $url})
                RETURN r.id as ref_id
                LIMIT 1
            """, {'url': reference_data['url']})
            
            if existing.single():
                # URL already exists, skip
                return None
            
            # Create new reference
            result = session.run("""
                MERGE (v:Vendor {name: $vendor_name})
                SET v.website = COALESCE(v.website, $vendor_website)
                
                CREATE (r:Reference {
                    id: randomUUID(),
                    url: $url,
                    raw_text: $raw_text,
                    scraped_date: datetime($scraped_date),
                    word_count: $word_count,
                    classified: false
                })
                
                MERGE (v)-[:PUBLISHED]->(r)
                
                RETURN r.id as ref_id
            """, {
                'vendor_name': vendor_name,
                'vendor_website': reference_data.get('vendor_website', ''),
                'url': reference_data['url'],
                'raw_text': reference_data['raw_text'],
                'scraped_date': reference_data['scraped_date'],
                'word_count': reference_data['word_count']
            })
            
            record = result.single()
            return record['ref_id'] if record else None
    
    def get_unclassified_references(self, limit=10):
        """
        Get references that need classification.
        
        Args:
            limit: Max number of references to return
            
        Returns:
            List of dicts with id, text, and url
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Reference)
                WHERE r.classified = false
                RETURN r.id as id, r.raw_text as text, r.url as url
                LIMIT $limit
            """, {'limit': limit})
            
            return [dict(record) for record in result]
    
    def update_classification(self, ref_id, classification_data):
        """
        Update reference with classification results.
        
        Args:
            ref_id: Reference ID
            classification_data: Dict with customer_name, industry, size, region, 
                                use_cases, tech_stack, quoted_text, outcomes, personas, etc.
        """
        with self.driver.session() as session:
            # Update reference and create customer
            session.run("""
                MATCH (r:Reference {id: $ref_id})
                SET r.classified = true,
                    r.classification_date = datetime(),
                    r.quoted_text = $quoted_text
                
                WITH r
                MERGE (c:Customer {name: $customer_name})
                SET c.size = $size,
                    c.region = $region,
                    c.country = $country
                MERGE (r)-[:FEATURES]->(c)
                
                WITH r, c
                MERGE (i:Industry {name: $industry})
                MERGE (c)-[:IN_INDUSTRY]->(i)
            """, {
                'ref_id': ref_id,
                'customer_name': classification_data.get('customer_name', 'Unknown'),
                'size': classification_data.get('company_size', 'Unknown'),
                'region': classification_data.get('region', 'Unknown'),
                'country': classification_data.get('country'),
                'industry': classification_data.get('industry', 'Other'),
                'quoted_text': classification_data.get('quoted_text', '')
            })
            
            # Create use case relationships
            use_cases = classification_data.get('use_cases', [])
            if use_cases:
                session.run("""
                    MATCH (r:Reference {id: $ref_id})
                    UNWIND $use_cases as uc_name
                    MERGE (uc:UseCase {name: uc_name})
                    MERGE (r)-[:ADDRESSES_USE_CASE]->(uc)
                """, {
                    'ref_id': ref_id,
                    'use_cases': use_cases
                })
            
            # Create technology relationships
            tech_stack = classification_data.get('tech_stack', [])
            if tech_stack:
                session.run("""
                    MATCH (r:Reference {id: $ref_id})
                    UNWIND $tech_stack as tech_name
                    MERGE (t:Technology {name: tech_name})
                    MERGE (r)-[:MENTIONS_TECH]->(t)
                """, {
                    'ref_id': ref_id,
                    'tech_stack': tech_stack
                })
            
            # Create outcome relationships
            outcomes = classification_data.get('outcomes', [])
            if outcomes:
                for outcome in outcomes:
                    metric = outcome.get('metric')
                    # Only set metric if it exists and is not empty
                    if metric:
                        session.run("""
                            MATCH (r:Reference {id: $ref_id})
                            MERGE (o:Outcome {
                                type: $type,
                                description: $description,
                                metric: $metric
                            })
                            MERGE (r)-[:ACHIEVED_OUTCOME]->(o)
                        """, {
                            'ref_id': ref_id,
                            'type': outcome.get('type', 'other'),
                            'description': outcome.get('description', ''),
                            'metric': metric
                        })
                    else:
                        # Create outcome without metric property
                        session.run("""
                            MATCH (r:Reference {id: $ref_id})
                            MERGE (o:Outcome {
                                type: $type,
                                description: $description
                            })
                            MERGE (r)-[:ACHIEVED_OUTCOME]->(o)
                        """, {
                            'ref_id': ref_id,
                            'type': outcome.get('type', 'other'),
                            'description': outcome.get('description', '')
                        })
            
            # Create persona relationships
            personas = classification_data.get('personas', [])
            if personas:
                for persona in personas:
                    session.run("""
                        MATCH (r:Reference {id: $ref_id})
                        MERGE (p:Persona {
                            title: $title,
                            seniority: $seniority
                        })
                        SET p.name = $name
                        MERGE (r)-[:MENTIONS_PERSONA]->(p)
                    """, {
                        'ref_id': ref_id,
                        'title': persona.get('title', ''),
                        'seniority': persona.get('seniority', ''),
                        'name': persona.get('name', '')
                    })
    
    def get_stats(self):
        """Get database statistics."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Reference)
                WITH count(r) as total_refs,
                     sum(CASE WHEN r.classified THEN 1 ELSE 0 END) as classified_refs
                
                MATCH (v:Vendor)
                WITH total_refs, classified_refs, count(v) as total_vendors
                
                MATCH (c:Customer)
                RETURN total_refs, classified_refs, total_vendors, count(c) as total_customers
            """)
            
            record = result.single()
            if record:
                return {
                    'total_references': record.get('total_refs', 0) or 0,
                    'classified_references': record.get('classified_refs', 0) or 0,
                    'total_vendors': record.get('total_vendors', 0) or 0,
                    'total_customers': record.get('total_customers', 0) or 0
                }
            else:
                # Empty database
                return {
                    'total_references': 0,
                    'classified_references': 0,
                    'total_vendors': 0,
                    'total_customers': 0
                }


if __name__ == '__main__':
    # Test connection
    client = Neo4jClient()
    
    if client.verify_connection():
        print("✓ Connected to Neo4j")
        client.create_indexes()
        stats = client.get_stats()
        print(f"Stats: {stats}")
    else:
        print("✗ Connection failed")
    
    client.close()

