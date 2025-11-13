"""Neo4j database client for customer reference intelligence."""

import re

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
            
            # Account name index
            session.run("""
                CREATE INDEX account_name IF NOT EXISTS 
                FOR (a:Account) ON (a.name)
            """)
            
            # Champion id index
            session.run("""
                CREATE INDEX champion_id IF NOT EXISTS 
                FOR (c:Champion) ON (c.id)
            """)
            
            # Material id index
            session.run("""
                CREATE INDEX material_id IF NOT EXISTS 
                FOR (m:Material) ON (m.id)
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
            classification_data: Dict with structured enrichment data from the classifier.
        """
        def _slugify(value: str | None) -> str | None:
            """Convert a string into a lowercase, hyphenated slug."""
            if not value:
                return None
            slug = re.sub(r'[^a-z0-9]+', '-', value.strip().lower())
            slug = re.sub(r'-{2,}', '-', slug).strip('-')
            return slug or None
        
        with self.driver.session() as session:
            customer_name = classification_data.get('customer_name') or 'Unknown'
            industry = classification_data.get('industry') or 'Other'
            company_size = classification_data.get('company_size') or 'Unknown'
            region = classification_data.get('region')
            country = classification_data.get('country')
            account_details = classification_data.get('account_details') or {}
            logo_url = account_details.get('logo_url')
            website = account_details.get('website')
            account_summary = account_details.get('summary')
            account_tagline = account_details.get('tagline')
            quoted_text = classification_data.get('quoted_text', '')
            use_cases = [uc for uc in (classification_data.get('use_cases') or []) if uc]
            tech_stack = [tech for tech in (classification_data.get('tech_stack') or []) if tech]
            outcomes = classification_data.get('outcomes') or []
            personas = classification_data.get('personas') or []
            champions = classification_data.get('champions') or []
            materials_input = classification_data.get('materials') or []
            
            primary_material = materials_input[0] if materials_input else {}
            primary_challenge = primary_material.get('challenge')
            primary_solution = primary_material.get('solution')
            primary_impact = primary_material.get('impact')
            primary_pitch = primary_material.get('elevator_pitch')
            primary_proof_points = [pp for pp in (primary_material.get('proof_points') or []) if pp]
            primary_language = primary_material.get('language')
            primary_region = primary_material.get('region')
            primary_country = primary_material.get('country')
            primary_product = primary_material.get('product')
            primary_quotes = [q for q in (primary_material.get('quotes') or []) if q]
            
            if not primary_region or primary_region == 'Unknown':
                primary_region = region if region and region != 'Unknown' else None
            if not primary_country:
                primary_country = country
            if not primary_language:
                primary_language = 'Unknown'
            
            material_ids: list[str] = []
            normalized_materials: list[dict] = []
            for material in materials_input:
                base_id = material.get('material_id') or material.get('url') or ref_id
                if base_id == ref_id and material.get('title'):
                    base_id = f"{customer_name}-{material.get('title')}"
                material_id = _slugify(str(base_id)) or _slugify(f"{customer_name}-{ref_id}") or ref_id
                
                normalized = {
                    'material_id': material_id,
                    'title': material.get('title'),
                    'content_type': material.get('content_type'),
                    'publish_date': material.get('publish_date'),
                    'url': material.get('url'),
                    'raw_text_excerpt': material.get('raw_text_excerpt'),
                    'country': material.get('country') or primary_country,
                    'region': material.get('region') or primary_region or 'Unknown',
                    'language': material.get('language') or primary_language,
                    'product': material.get('product') or primary_product,
                    'challenge': material.get('challenge') or primary_challenge,
                    'solution': material.get('solution') or primary_solution,
                    'impact': material.get('impact') or primary_impact,
                    'elevator_pitch': material.get('elevator_pitch') or primary_pitch,
                    'proof_points': [pp for pp in (material.get('proof_points') or []) if pp],
                    'quotes': [q for q in (material.get('quotes') or []) if q],
                    'champion_role': material.get('champion_role'),
                    'embedding': material.get('embedding')
                }
                normalized_materials.append(normalized)
                material_ids.append(material_id)
            
            if not material_ids:
                fallback_material_id = _slugify(f"{customer_name}-{ref_id}") or ref_id
                material_ids.append(fallback_material_id)
            else:
                material_ids = list(dict.fromkeys(material_ids))
            
            account_region = region if region and region != 'Unknown' else None
            account_country = country
            if not primary_region:
                primary_region = 'Unknown'
            if not primary_country:
                primary_country = account_country
            
            session.run("""
                MATCH (r:Reference {id: $ref_id})
                OPTIONAL MATCH (r)<-[:PUBLISHED]-(vendor:Vendor)
                SET r.classified = true,
                    r.classification_date = datetime(),
                    r.quoted_text = $quoted_text,
                    r.challenge = COALESCE($primary_challenge, r.challenge),
                    r.solution = COALESCE($primary_solution, r.solution),
                    r.impact = COALESCE($primary_impact, r.impact),
                    r.elevator_pitch = COALESCE($primary_pitch, r.elevator_pitch),
                    r.proof_points = CASE 
                        WHEN $primary_proof_points = [] THEN r.proof_points
                        ELSE $primary_proof_points
                    END,
                    r.language = COALESCE($primary_language, r.language),
                    r.region = COALESCE($primary_region, r.region),
                    r.country = COALESCE($primary_country, r.country),
                    r.product_focus = COALESCE($primary_product, r.product_focus),
                    r.material_ids = $material_ids,
                    r.additional_quotes = CASE 
                        WHEN $primary_quotes = [] THEN r.additional_quotes
                        ELSE $primary_quotes
                    END
                WITH r, vendor
                MERGE (account:Account:Customer {name: $customer_name})
                SET account.size = $company_size,
                    account.region = COALESCE($account_region, account.region, 'Unknown'),
                    account.country = COALESCE($account_country, account.country),
                    account.logo_url = COALESCE($logo_url, account.logo_url),
                    account.website = COALESCE($website, account.website),
                    account.summary = COALESCE($account_summary, account.summary),
                    account.tagline = COALESCE($account_tagline, account.tagline)
                MERGE (r)-[:FEATURES]->(account)
                MERGE (account)-[:HAS_REFERENCE]->(r)
                WITH r, account, vendor
                MERGE (industry:Industry {name: $industry})
                MERGE (account)-[:IN_INDUSTRY]->(industry)
                MERGE (r)-[:IN_INDUSTRY]->(industry)
                WITH r, account, vendor, industry
                FOREACH (_ IN CASE WHEN vendor IS NULL THEN [] ELSE [1] END |
                    MERGE (vendor)-[:HAS_CUSTOMER]->(account)
                )
            """, {
                'ref_id': ref_id,
                'quoted_text': quoted_text,
                'customer_name': customer_name,
                'company_size': company_size,
                'account_region': account_region,
                'account_country': account_country,
                'logo_url': logo_url,
                'website': website,
                'account_summary': account_summary,
                'account_tagline': account_tagline,
                'industry': industry,
                'primary_challenge': primary_challenge,
                'primary_solution': primary_solution,
                'primary_impact': primary_impact,
                'primary_pitch': primary_pitch,
                'primary_proof_points': primary_proof_points,
                'primary_language': primary_language,
                'primary_region': primary_region,
                'primary_country': primary_country,
                'primary_product': primary_product,
                'material_ids': material_ids,
                'primary_quotes': primary_quotes
            })
            
            # Create use case relationships
            if use_cases:
                session.run("""
                    MATCH (r:Reference {id: $ref_id})-[:FEATURES]->(account:Account)
                    UNWIND $use_cases as uc_name
                    MERGE (uc:UseCase {name: uc_name})
                    MERGE (r)-[:ADDRESSES_USE_CASE]->(uc)
                    MERGE (r)-[:HAS_USE_CASE]->(uc)
                    MERGE (account)-[:HAS_USE_CASE]->(uc)
                """, {
                    'ref_id': ref_id,
                    'use_cases': use_cases
                })
            
            # Create technology relationships
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
            if outcomes:
                for outcome in outcomes:
                    description = outcome.get('description', '')
                    outcome_type = outcome.get('type', 'other')
                    metric = outcome.get('metric')
                    
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
                            'type': outcome_type,
                            'description': description,
                            'metric': metric
                        })
                    else:
                        session.run("""
                            MATCH (r:Reference {id: $ref_id})
                            MERGE (o:Outcome {
                                type: $type,
                                description: $description
                            })
                            MERGE (r)-[:ACHIEVED_OUTCOME]->(o)
                        """, {
                            'ref_id': ref_id,
                            'type': outcome_type,
                            'description': description
                        })
            
            # Create persona relationships
            if personas:
                for persona in personas:
                    title = persona.get('title', '')
                    seniority = persona.get('seniority', '')
                    name = persona.get('name', '')
                    
                    if not title:
                        continue
                    
                    session.run("""
                        MATCH (r:Reference {id: $ref_id})
                        MERGE (p:Persona {
                            title: $title,
                            seniority: $seniority
                        })
                        SET p.name = COALESCE($name, p.name)
                        MERGE (r)-[:MENTIONS_PERSONA]->(p)
                    """, {
                        'ref_id': ref_id,
                        'title': title,
                        'seniority': seniority,
                        'name': name or None
                    })
            
            # Create champion relationships
            if champions:
                for champion in champions:
                    champion_name = champion.get('name')
                    champion_title = champion.get('title')
                    champion_role = champion.get('role')
                    champion_seniority = champion.get('seniority') or 'Unknown'
                    champion_quotes = [q for q in (champion.get('quotes') or []) if q]
                    
                    if not any([champion_name, champion_title, champion_role, champion_quotes]):
                        continue
                    
                    champion_id = champion.get('champion_id')
                    if not champion_id:
                        slug_source = "-".join(
                            filter(
                                None,
                                [customer_name, champion_name, champion_title, champion_role]
                            )
                        )
                        champion_id = _slugify(slug_source) or _slugify(f"{customer_name}-{ref_id}-champion")
                    else:
                        champion_id = _slugify(champion_id) or champion_id
                    
                    session.run("""
                        MATCH (r:Reference {id: $ref_id})-[:FEATURES]->(account:Account)
                        MERGE (champ:Champion {id: $champion_id})
                        SET champ.name = COALESCE($champion_name, champ.name),
                            champ.title = COALESCE($champion_title, champ.title),
                            champ.role = COALESCE($champion_role, champ.role),
                            champ.seniority = COALESCE($champion_seniority, champ.seniority),
                            champ.quotes = CASE 
                                WHEN $champion_quotes = [] THEN champ.quotes 
                                ELSE $champion_quotes 
                            END,
                            champ.account_name = account.name
                        MERGE (account)-[:HAS_CHAMPION]->(champ)
                        MERGE (r)-[:HAS_CHAMPION]->(champ)
                    """, {
                        'ref_id': ref_id,
                        'champion_id': champion_id,
                        'champion_name': champion_name,
                        'champion_title': champion_title,
                        'champion_role': champion_role,
                        'champion_seniority': champion_seniority,
                        'champion_quotes': champion_quotes
                    })
            
            # Create material relationships
            if normalized_materials:
                for material in normalized_materials:
                    session.run("""
                        MATCH (r:Reference {id: $ref_id})
                        MERGE (m:Material {id: $material_id})
                        SET m.title = COALESCE($title, m.title),
                            m.content_type = COALESCE($content_type, m.content_type),
                            m.publish_date = COALESCE($publish_date, m.publish_date),
                            m.url = COALESCE($url, m.url),
                            m.raw_text_excerpt = COALESCE($raw_text_excerpt, m.raw_text_excerpt),
                            m.country = COALESCE($country, m.country),
                            m.region = COALESCE($region, m.region),
                            m.language = COALESCE($language, m.language),
                            m.product = COALESCE($product, m.product),
                            m.challenge = COALESCE($challenge, m.challenge),
                            m.solution = COALESCE($solution, m.solution),
                            m.impact = COALESCE($impact, m.impact),
                            m.elevator_pitch = COALESCE($elevator_pitch, m.elevator_pitch),
                            m.proof_points = CASE 
                                WHEN $proof_points = [] THEN m.proof_points 
                                ELSE $proof_points 
                            END,
                            m.quotes = CASE 
                                WHEN $quotes = [] THEN m.quotes 
                                ELSE $quotes 
                            END,
                            m.champion_role = COALESCE($champion_role, m.champion_role),
                            m.embedding = COALESCE($embedding, m.embedding)
                        MERGE (r)-[:HAS_MATERIAL]->(m)
                    """, {
                        'ref_id': ref_id,
                        'material_id': material['material_id'],
                        'title': material.get('title'),
                        'content_type': material.get('content_type'),
                        'publish_date': material.get('publish_date'),
                        'url': material.get('url'),
                        'raw_text_excerpt': material.get('raw_text_excerpt'),
                        'country': material.get('country'),
                        'region': material.get('region'),
                        'language': material.get('language'),
                        'product': material.get('product'),
                        'challenge': material.get('challenge'),
                        'solution': material.get('solution'),
                        'impact': material.get('impact'),
                        'elevator_pitch': material.get('elevator_pitch'),
                        'proof_points': material.get('proof_points'),
                        'quotes': material.get('quotes'),
                        'champion_role': material.get('champion_role'),
                        'embedding': material.get('embedding')
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

