Project Documentation for Cursor
I'll create three comprehensive documents for you:
1. PROJECT.md - Comprehensive Background
markdown# Customer Reference Intelligence Platform

## Project Vision

Build an AI-powered competitive intelligence platform that helps B2B companies (starting with the data/database industry) discover, analyze, and leverage customer references across their competitive landscape using graph database technology.

## The Problem

Customer marketing and sales teams face several challenges:

1. **Finding the right reference**: When pursuing a prospect, teams struggle to identify which existing customer stories best match the prospect's profile (industry, use case, company size, region)

2. **Competitive blindspots**: Companies don't know which competitors have the strongest customer proof in specific industries, use cases, or geographies

3. **Reference program intelligence**: Customer marketing leaders lack data-driven insights about:
   - Which customers are willing to participate in references (advocacy propensity)
   - Market coverage gaps in their reference portfolio
   - Which use cases or industries need more customer stories

4. **Relationship context**: Even when a good reference match is found, teams don't know who internally has the best relationship with that customer to make the ask

## The Solution

A graph-based intelligence platform that:

1. **Scrapes and structures** customer references from competitor websites across an industry vertical
2. **Classifies content** using LLMs to extract: industries, use cases, personas, outcomes, tech stacks
3. **Enables similarity search** to find the best reference matches for any prospect profile
4. **Reveals patterns** about competitive positioning, market coverage, and advocacy networks

## Why a Graph Database?

Customer reference intelligence is inherently a graph problem:

- **Customers** appear in references from multiple vendors
- **Use cases** cluster with specific industries and company profiles  
- **Technologies** co-occur in customer tech stacks
- **Relationships** between people and customers determine reference viability
- **Similarity** is multi-dimensional: not just "same industry" but "same industry + similar use case + comparable size + overlapping tech stack"

These are graph traversal and pattern matching problems that are awkward in relational databases but natural in Neo4j.

## V1 Scope

### Target Market: Data/Database Industry

**Companies to scrape (25-30 vendors):**

**Tier 1 (Priority):**
- Cloud Data Warehouses: Snowflake, Databricks, BigQuery (GCP), Redshift (AWS), Synapse (Azure)
- Modern Data Stack: Fivetran, dbt Labs, Airbyte, Stitch
- Operational Databases: MongoDB, PostgreSQL variants (Timescale, Crunchy Data), DataStax (Cassandra)
- Graph Databases: Neo4j, TigerGraph
- Analytics/BI: Looker, Tableau, Power BI, Domo

**Tier 2 (Later):**
- Streaming: Confluent, Redpanda, Materialize
- Data Observability: Monte Carlo, Datafold
- Reverse ETL: Hightouch, Census
- Data Catalogs: Alation, Collibra

### Core Features for V1

1. **Web Scraper**: Extract customer references from vendor websites
2. **AI Classifier**: Use Claude to extract structured data from raw reference text
3. **Graph Loader**: Load structured data into Neo4j (AuraDB Free)
4. **Similarity Search**: Find customer references that match a prospect profile
5. **Simple UI**: Streamlit app for searching and exploring data

### What's NOT in V1

- Relationship tracking (internal employee connections)
- Automated re-scraping / data refresh
- Multi-tenancy / user accounts
- Advanced analytics dashboards
- Mobile app
- API access

## Technical Architecture

### Tech Stack

- **Language**: Python 3.11+
- **Graph Database**: Neo4j AuraDB Free Tier
- **LLM**: Anthropic Claude (claude-sonnet-4)
- **Web Scraping**: BeautifulSoup4, Playwright (for JS-heavy sites)
- **Frontend**: Streamlit
- **Environment Management**: python-venv or uv

### Data Model

#### Nodes
```cypher
(:Vendor {name, website, industry_focus})
(:Customer {name, size, region, country})
(:Reference {id, url, type, raw_text, raw_html, scraped_date, word_count, quoted_text, classified})
(:Industry {name})
(:UseCase {name, description})
(:Persona {title, seniority})
(:Outcome {type, description, metric})
(:Technology {name, category})
```

#### Relationships
```cypher
(Vendor)-[:PUBLISHED]->(Reference)
(Reference)-[:FEATURES]->(Customer)
(Customer)-[:IN_INDUSTRY]->(Industry)
(Customer)-[:HAS_SIZE]->(CompanySize)
(Reference)-[:ADDRESSES_USE_CASE]->(UseCase)
(Reference)-[:ACHIEVED_OUTCOME]->(Outcome)
(Reference)-[:MENTIONS_PERSONA]->(Persona)
(Customer)-[:USES_TECH]->(Technology)
```

### Data Flow
```
1. Scrape → Raw HTML/Text
2. Load Raw → Neo4j (with classified=false flag)
3. Classify → Use Claude to extract structured data
4. Enrich Graph → Create nodes and relationships from classification
5. Query → Similarity search, analysis, reporting
```

## Classification Schema

### Predefined Taxonomies

**Industries:**
- Financial Services
- Healthcare & Life Sciences  
- Retail & E-commerce
- Technology & Software
- Manufacturing
- Telecommunications
- Media & Entertainment
- Travel & Hospitality
- Energy & Utilities
- Government & Public Sector
- Education

**Use Cases:**
- Real-time Analytics
- Data Migration
- Data Lakehouse/Lake
- ML/AI & Predictive Analytics
- Data Governance & Compliance
- Customer 360
- Fraud Detection
- Supply Chain Optimization
- Business Intelligence & Reporting
- Data Integration/ETL
- IoT & Sensor Data
- Recommendation Engines
- Operational Analytics
- Data Sharing/Collaboration

**Company Sizes:**
- Enterprise (>5000 employees)
- Mid-Market (500-5000 employees)
- SMB (<500 employees)
- Startup
- Unknown

**Regions:**
- North America
- EMEA (Europe, Middle East, Africa)
- APAC (Asia-Pacific)
- LATAM (Latin America)

## Success Metrics for V1

1. Successfully scrape 10+ vendors (100+ customer references)
2. Classification accuracy >85% (manual QA on 50 references)
3. Similarity search returns relevant results in <2 seconds
4. 3+ customer marketing professionals say "I'd pay for this"
5. Discover at least 3 non-obvious competitive insights

## Development Roadmap

### Phase 1: Proof of Concept (Weeks 1-2)
- Scrape Snowflake customer references (50+ references)
- Load raw text into AuraDB Free
- Build Claude classification function
- Validate data quality

### Phase 2: Core Platform (Weeks 3-4)
- Scrape 5 more vendors (Databricks, Fivetran, MongoDB, Looker)
- Refine classification prompts
- Build similarity search queries
- Create basic Streamlit UI

### Phase 3: Polish & Validate (Weeks 5-6)
- Scrape remaining Tier 1 vendors
- Add filtering and browsing features
- User testing with 3-5 customer marketing friends
- Documentation and demo preparation

### Phase 4: Post-V1 (Future)
- Relationship tracking integration
- Automated re-scraping
- Additional industry verticals
- SaaS productization

## Repository Structure
```
customer-reference-intelligence/
├── README.md
├── PROJECT.md (this file)
├── agents.md (Cursor AI context)
├── requirements.txt
├── .env.example
├── .gitignore
├── src/
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   ├── snowflake_scraper.py
│   │   ├── databricks_scraper.py
│   │   └── ...
│   ├── classifiers/
│   │   ├── __init__.py
│   │   ├── claude_classifier.py
│   │   └── prompt_templates.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── neo4j_client.py
│   │   ├── schema.py
│   │   └── queries.py
│   ├── ui/
│   │   ├── __init__.py
│   │   └── streamlit_app.py
│   └── utils/
│       ├── __init__.py
│       └── config.py
├── data/
│   ├── taxonomies/
│   │   ├── industries.json
│   │   ├── use_cases.json
│   │   └── company_sizes.json
│   └── scraped/ (gitignored)
├── tests/
│   ├── test_scrapers.py
│   ├── test_classifier.py
│   └── test_graph.py
└── notebooks/
    └── exploration.ipynb
```

## Environment Variables
```bash
# Neo4j AuraDB
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optional: for rate limiting
SCRAPE_DELAY_SECONDS=2
```

## Key Design Decisions

1. **Store raw content in Neo4j**: For v1 scale (~100-200 references), storing raw_text as a property is simpler than a hybrid database architecture

2. **Separate scraping from classification**: Scrape once, classify/re-classify many times as we improve prompts

3. **Idempotent operations**: All data loading should be MERGE-based so we can re-run safely

4. **Flag-based processing**: Use `classified=false` flag to track which references need classification

5. **JSON for taxonomies**: Keep predefined lists in version-controlled JSON files

## Future Enhancements (Post-V1)

### V1.5: Relationship Intelligence
- Integrate with email/CRM to map employee-customer relationships
- "Best-placed contact" scoring algorithm
- Relationship strength over time tracking

### V2: SaaS Product
- Multi-tenancy
- User authentication
- Subscription tiers
- API access
- Automated weekly scraping

### V3: Additional Verticals
- Fintech
- Healthcare Tech
- Martech
- Cybersecurity

### V4: Advanced Features
- Competitive positioning reports
- Advocacy propensity scoring
- Reference portfolio gap analysis
- Benchmark metrics dashboard

## License

TBD - Private/Proprietary for now

## Author

Theo - Neo4j Customer Marketing
2. agents.md - Cursor AI Context
markdown# AI Agent Instructions for Customer Reference Intelligence Platform

This file provides context for AI coding assistants (like Cursor) working on this project.

## Project Overview

This is a competitive intelligence platform for B2B customer marketing teams. We scrape customer references from company websites, classify them using LLMs, store them in a Neo4j graph database, and enable similarity search to find the best reference matches for sales opportunities.

**Current Phase**: V1 - Proof of Concept
**Target Industry**: Data/Database companies (Snowflake, Databricks, etc.)

## Key Technical Context

### Tech Stack
- **Python 3.11+** for all backend code
- **Neo4j AuraDB Free** for graph storage (cloud-hosted Neo4j)
- **Anthropic Claude API** (claude-sonnet-4) for content classification
- **BeautifulSoup4 / Playwright** for web scraping
- **Streamlit** for UI (later phase)
- **python-dotenv** for environment management

### Critical Design Patterns

#### 1. Separation of Concerns
```
Scraping → Load Raw to DB → Classify → Enrich Graph
```
Each step is a separate function/module. Raw content is always preserved.

#### 2. Idempotent Graph Operations
Always use MERGE, never CREATE for nodes that might already exist:
```python
# ✅ GOOD - Won't create duplicates
session.run("""
    MERGE (c:Customer {name: $name})
    SET c.size = $size
""", params)

# ❌ BAD - Creates duplicates on re-run
session.run("""
    CREATE (c:Customer {name: $name, size: $size})
""", params)
```

#### 3. Processing Flags
References have a `classified` boolean property:
- `classified=false` means raw text needs classification
- After classification completes, set `classified=true`
- This lets us reprocess if we improve classification prompts

#### 4. Error Handling for External APIs
Always handle rate limits and network errors:
```python
import time
from anthropic import APIError, RateLimitError

def classify_with_retry(text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.messages.create(...)
        except RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
        except APIError as e:
            print(f"API error: {e}")
            raise
```

#### 5. Schema Consistency
Use the predefined taxonomies in `data/taxonomies/` for classification:
- `industries.json` - Industry categories
- `use_cases.json` - Use case types
- `company_sizes.json` - Company size bands

Load these into prompts to ensure consistent classification.

## Graph Schema

### Core Nodes
```cypher
// Vendor who published the reference
(:Vendor {
    name: string,           // "Snowflake"
    website: string,        // "https://snowflake.com"
    scraped_date: datetime
})

// Customer being referenced
(:Customer {
    name: string,           // "Capital One"
    size: string,           // "Enterprise"
    region: string,         // "North America"
    country: string         // "United States" (optional)
})

// The reference content itself
(:Reference {
    id: string,             // UUID or vendor_ref_001
    url: string,
    type: string,           // "case_study", "video", "blog"
    raw_text: string,       // Full scraped text
    raw_html: string,       // Original HTML (optional)
    scraped_date: datetime,
    word_count: integer,
    quoted_text: string,    // Best customer quote
    classified: boolean,    // Processing flag
    classification_date: datetime
})

// Industry categories
(:Industry {name: string})  // "Financial Services"

// Use cases solved
(:UseCase {
    name: string,           // "Real-time Analytics"
    description: string     // (optional)
})

// Job titles/personas featured
(:Persona {
    title: string,          // "Chief Data Officer"
    seniority: string       // "C-Level", "VP", "Director"
})

// Business outcomes achieved
(:Outcome {
    type: string,           // "performance", "cost_savings", "revenue_impact"
    description: string,    // "10x faster queries"
    metric: string          // (optional) "10x"
})

// Technologies mentioned
(:Technology {
    name: string,           // "AWS", "dbt"
    category: string        // "Cloud Platform", "Transformation Tool"
})
```

### Core Relationships
```cypher
(Vendor)-[:PUBLISHED]->(Reference)
(Reference)-[:FEATURES]->(Customer)
(Customer)-[:IN_INDUSTRY]->(Industry)
(Reference)-[:ADDRESSES_USE_CASE]->(UseCase)
(Reference)-[:ACHIEVED_OUTCOME]->(Outcome)
(Reference)-[:MENTIONS_PERSONA]->(Persona)
(Customer)-[:USES_TECH]->(Technology)
```

## Common Tasks & How to Approach Them

### Task: Add a New Scraper

1. Create new file in `src/scrapers/{vendor}_scraper.py`
2. Inherit from `BaseScraper` class (when it exists)
3. Implement these methods:
   - `get_reference_urls()` - Returns list of URLs to scrape
   - `scrape_reference(url)` - Returns dict with raw_text, raw_html, metadata
4. Handle pagination if needed
5. Add rate limiting (2-3 second delays between requests)
6. Return consistent schema:
```python
{
    'url': str,
    'raw_text': str,
    'raw_html': str,  # optional
    'customer_name': str,  # if obvious from URL/title
    'scraped_date': str,  # ISO format
    'word_count': int
}
```

### Task: Improve Classification Prompt

1. Edit `src/classifiers/prompt_templates.py`
2. Load taxonomies from `data/taxonomies/` into prompt
3. Always request structured JSON output
4. Include examples for clarity
5. Test on 5-10 diverse references before deploying
6. To reprocess everything: Set all references to `classified=false` and re-run

### Task: Add New Graph Query

1. Add to `src/graph/queries.py`
2. Write as a function that takes parameters
3. Return Python data structures (list of dicts), not raw Neo4j results
4. Add docstring with example usage
5. Consider query performance - use indexes if needed:
```cypher
CREATE INDEX customer_name IF NOT EXISTS FOR (c:Customer) ON (c.name)
CREATE INDEX reference_url IF NOT EXISTS FOR (r:Reference) ON (r.url)
```

### Task: Debug Graph Data

Use Neo4j Browser (accessible from AuraDB console):
```cypher
// Count references by vendor
MATCH (v:Vendor)-[:PUBLISHED]->(r:Reference)
RETURN v.name, count(r) as ref_count
ORDER BY ref_count DESC

// Find unclassified references
MATCH (r:Reference)
WHERE r.classified = false
RETURN r.url, r.scraped_date
LIMIT 10

// Check a specific customer's data
MATCH (c:Customer {name: "Capital One"})(uc:UseCase)
RETURN c, r, collect(uc.name) as use_cases
```

## Common Pitfalls to Avoid

### 1. Don't Create Duplicate Nodes
Always use MERGE with a unique property (usually `name` or `id`)

### 2. Don't Store Secrets in Code
Use environment variables loaded from `.env`:
```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('ANTHROPIC_API_KEY')
```

### 3. Don't Scrape Too Fast
Always add delays between requests (2-3 seconds minimum):
```python
import time

for url in urls:
    data = scrape_url(url)
    time.sleep(2)  # Be respectful
```

### 4. Don't Assume HTML Structure
Websites change. Always:
- Check if elements exist before accessing
- Use try/except for parsing
- Log when expected elements are missing
```python
try:
    customer_name = soup.find('h1', class_='customer-name').text.strip()
except AttributeError:
    print(f"Could not find customer name at {url}")
    customer_name = "Unknown"
```

### 5. Don't Ignore Claude API Costs
Claude Sonnet charges per token. For v1:
- ~100-200 references to classify
- ~2,000 tokens per reference (input + output)
- ~$0.01 per classification
- Total cost: $1-2 for v1 dataset

Track token usage during development.

## File Organization Conventions

### Module Naming
- `{vendor}_scraper.py` for scrapers
- `{purpose}_classifier.py` for classifiers
- `{entity}_queries.py` for query modules

### Function Naming
- `scrape_*` for scraping functions
- `classify_*` for classification functions
- `load_*` for database operations
- `get_*` for queries that fetch data
- `create_*` for queries that create data

### Variable Naming
- `*_url` for URLs
- `*_id` for identifiers
- `raw_*` for unprocessed data
- `*_result` for Neo4j results
- `*_data` for Python dicts/lists

## Testing Approach

For v1, keep testing simple:

1. **Manual QA**: Inspect 10-20 scraped references in Neo4j Browser
2. **Classification accuracy**: Manually review 20 classifications vs source material
3. **Query correctness**: Run similarity search on known examples, verify results make sense
4. **End-to-end**: Scrape vendor → Classify → Query → Visual inspection

Automated tests can come in v2.

## When to Ask for Help

If you encounter:
- Websites with heavy JavaScript (need Playwright)
- Claude API rate limits that can't be solved with exponential backoff
- Neo4j query performance issues
- Classification accuracy below 80% after prompt tuning
- Data model questions (e.g., should this be a node or property?)

Flag it and ask rather than guessing.

## Current Sprint Focus

**Phase 1: Proof of Concept** (Current)

Tasks:
1. ✅ Set up project structure
2. ⏳ Build Snowflake scraper
3. ⏳ Load raw data to AuraDB
4. ⏳ Create Claude classification function
5. ⏳ Validate data quality

Next: Once Snowflake is working end-to-end, replicate for Databricks.

## Useful Neo4j Cypher Patterns

### Loading raw data
```cypher
MERGE (v:Vendor {name: $vendor_name})
CREATE (r:Reference {
    id: randomUUID(),
    url: $url,
    raw_text: $raw_text,
    scraped_date: datetime(),
    classified: false
})
MERGE (v)-[:PUBLISHED]->(r)
RETURN r.id
```

### Classification update
```cypher
MATCH (r:Reference {id: $ref_id})
SET r.classified = true,
    r.classification_date = datetime(),
    r.quoted_text = $quoted_text

WITH r
MERGE (c:Customer {name: $customer_name})
SET c.size = $size, c.region = $region
MERGE (r)-[:FEATURES]->(c)

WITH r, c
MERGE (i:Industry {name: $industry})
MERGE (c)-[:IN_INDUSTRY]->(i)

WITH r
UNWIND $use_cases as uc_name
MERGE (uc:UseCase {name: uc_name})
MERGE (r)-[:ADDRESSES_USE_CASE]->(uc)
```

### Similarity search skeleton
```cypher
// Given a prospect profile, find similar customers
MATCH (c:Customer)-[:IN_INDUSTRY]->(i:Industry {name: $industry})
WHERE c.region = $region AND c.size = $size

MATCH (c)(uc:UseCase)
WHERE uc.name IN $use_cases

RETURN c, count(DISTINCT r) as ref_count, collect(DISTINCT uc.name) as matching_use_cases
ORDER BY ref_count DESC
LIMIT 10
```

## Remember

- **Start simple**: Get one vendor working end-to-end before scaling
- **Preserve raw data**: Always keep original scraped text
- **Iterate on prompts**: Classification will improve with tuning
- **Use the graph**: When queries get complex, the graph relationships make them simple
- **Focus on v1 scope**: Resist feature creep until core value is proven

Good luck! This is going to be a powerful tool.
3. INITIAL_PLAN.md - Test Implementation Plan
markdown# Phase 1 Test Plan: Snowflake → AuraDB → Classification

## Objective

Build and validate the core data pipeline with Snowflake as the test vendor:
1. Scrape Snowflake customer reference pages
2. Load raw text into AuraDB Free instance
3. Classify content using Claude API
4. Validate data quality

**Success Criteria**: 20+ Snowflake references successfully scraped, loaded, classified, and queryable with >80% accuracy.

## Prerequisites

### 1. Set Up AuraDB Free Instance

1. Go to https://console.neo4j.io/
2. Sign up / Log in
3. Create new instance:
   - Name: `customer-ref-intelligence-dev`
   - Type: AuraDB Free
   - Region: Choose closest to you
4. Save credentials:
   - Connection URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: `<generated>`
5. Test connection in Neo4j Browser

### 2. Get Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up / Log in
3. Create API key
4. Copy key: `sk-ant-xxxxx`

### 3. Set Up Python Environment
```bash
# Create project directory
mkdir customer-reference-intelligence
cd customer-reference-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install neo4j anthropic beautifulsoup4 requests python-dotenv

# Create .env file
cat > .env << EOL
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
ANTHROPIC_API_KEY=sk-ant-xxxxx
EOL
```

### 4. Create Project Structure
```bash
mkdir -p src/{scrapers,classifiers,graph,utils}
mkdir -p data/{taxonomies,scraped}
mkdir tests

touch src/__init__.py
touch src/scrapers/__init__.py
touch src/classifiers/__init__.py
touch src/graph/__init__.py
touch src/utils/__init__.py
```

## Step 1: Create Taxonomies

**File: `data/taxonomies/industries.json`**
```json
{
  "industries": [
    "Financial Services",
    "Healthcare & Life Sciences",
    "Retail & E-commerce",
    "Technology & Software",
    "Manufacturing",
    "Telecommunications",
    "Media & Entertainment",
    "Travel & Hospitality",
    "Energy & Utilities",
    "Government & Public Sector",
    "Education",
    "Other"
  ]
}
```

**File: `data/taxonomies/use_cases.json`**
```json
{
  "use_cases": [
    "Real-time Analytics",
    "Data Migration",
    "Data Lakehouse/Data Lake",
    "ML/AI & Predictive Analytics",
    "Data Governance & Compliance",
    "Customer 360",
    "Fraud Detection",
    "Supply Chain Optimization",
    "Business Intelligence & Reporting",
    "Data Integration/ETL",
    "IoT & Sensor Data",
    "Recommendation Engines",
    "Financial Analytics",
    "Operational Analytics",
    "Data Sharing/Collaboration"
  ]
}
```

**File: `data/taxonomies/company_sizes.json`**
```json
{
  "company_sizes": [
    "Enterprise (>5000 employees)",
    "Mid-Market (500-5000 employees)",
    "SMB (<500 employees)",
    "Startup",
    "Unknown"
  ]
}
```

## Step 2: Build Neo4j Client

**File: `src/graph/neo4j_client.py`**
```python
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
        
        Args:
            vendor_name: Name of vendor who published reference
            reference_data: Dict with keys: url, raw_text, scraped_date, word_count
            
        Returns:
            Created reference ID
        """
        with self.driver.session() as session:
            result = session.run("""
                MERGE (v:Vendor {name: $vendor_name})
                
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
                'url': reference_data['url'],
                'raw_text': reference_data['raw_text'],
                'scraped_date': reference_data['scraped_date'],
                'word_count': reference_data['word_count']
            })
            
            record = result.single()
            return record['ref_id']
    
    def get_unclassified_references(self, limit=10):
        """
        Get references that need classification.
        
        Args:
            limit: Max number of references to return
            
        Returns:
            List of dicts with id and raw_text
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
                                use_cases, tech_stack, quoted_text, etc.
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (r:Reference {id: $ref_id})
                SET r.classified = true,
                    r.classification_date = datetime(),
                    r.quoted_text = $quoted_text
                
                WITH r
                MERGE (c:Customer {name: $customer_name})
                SET c.size = $size,
                    c.region = $region
                MERGE (r)-[:FEATURES]->(c)
                
                WITH r, c
                MERGE (i:Industry {name: $industry})
                MERGE (c)-[:IN_INDUSTRY]->(i)
                
                WITH r
                UNWIND $use_cases as uc_name
                MERGE (uc:UseCase {name: uc_name})
                MERGE (r)-[:ADDRESSES_USE_CASE]->(uc)
                
                WITH r
                UNWIND $tech_stack as tech_name
                MERGE (t:Technology {name: tech_name})
                MERGE (r)-[:MENTIONS_TECH]->(t)
            """, {
                'ref_id': ref_id,
                'customer_name': classification_data.get('customer_name', 'Unknown'),
                'size': classification_data.get('company_size', 'Unknown'),
                'region': classification_data.get('region', 'Unknown'),
                'industry': classification_data.get('industry', 'Other'),
                'use_cases': classification_data.get('use_cases', []),
                'tech_stack': classification_data.get('tech_stack', []),
                'quoted_text': classification_data.get('quoted_text', '')
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
            return {
                'total_references': record['total_refs'],
                'classified_references': record['classified_refs'],
                'total_vendors': record['total_vendors'],
                'total_customers': record['total_customers']
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
```

## Step 3: Build Snowflake Scraper

**File: `src/scrapers/snowflake_scraper.py`**
```python
"""Scraper for Snowflake customer references."""

import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import urljoin


class SnowflakeScraper:
    """Scrape customer references from Snowflake website."""
    
    BASE_URL = "https://www.snowflake.com"
    CUSTOMERS_PAGE = "/en/why-snowflake/customers/"
    
    def __init__(self, delay=2):
        """
        Initialize scraper.
        
        Args:
            delay: Seconds to wait between requests (be respectful)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def get_customer_reference_urls(self):
        """
        Get list of customer reference URLs from main customers page.
        
        Returns:
            List of full URLs to customer reference pages
        """
        print(f"Fetching customer list from {self.BASE_URL + self.CUSTOMERS_PAGE}")
        
        try:
            response = self.session.get(self.BASE_URL + self.CUSTOMERS_PAGE)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links that look like customer pages
            # This selector may need adjustment based on Snowflake's actual HTML
            links = []
            
            # Method 1: Look for links in customer cards/sections
            customer_links = soup.find_all('a', href=True)
            for link in customer_links:
                href = link['href']
                # Customer pages typically follow pattern: /customers/{company-name}
                if '/customers/' in href and href != self.CUSTOMERS_PAGE:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in links:
                        links.append(full_url)
            
            print(f"Found {len(links)} customer reference URLs")
            return links[:25]  # Limit to 25 for initial test
            
        except Exception as e:
            print(f"Error fetching customer URLs: {e}")
            return []
    
    def scrape_reference(self, url):
        """
        Scrape a single customer reference page.
        
        Args:
            url: URL of customer reference page
            
        Returns:
            Dict with raw_text, url, customer_name, scraped_date, word_count
        """
        print(f"Scraping: {url}")
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract customer name (usually in title or h1)
            customer_name = "Unknown"
            title_tag = soup.find('h1')
            if title_tag:
                customer_name = title_tag.get_text(strip=True)
            
            # Extract main content text
            # Remove nav, footer, scripts, styles
            for tag in soup(['nav', 'footer', 'script', 'style', 'header']):
                tag.decompose()
            
            # Get clean text
            raw_text = soup.get_text(separator='\n', strip=True)
            
            # Clean up multiple newlines
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            raw_text = '\n'.join(lines)
            
            word_count = len(raw_text.split())
            
            return {
                'url': url,
                'customer_name': customer_name,
                'raw_text': raw_text,
                'scraped_date': datetime.now().isoformat(),
                'word_count': word_count
            }
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    def scrape_all(self):
        """
        Scrape all customer references.
        
        Returns:
            List of reference dicts
        """
        urls = self.get_customer_reference_urls()
        references = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]")
            
            ref_data = self.scrape_reference(url)
            if ref_data:
                references.append(ref_data)
                print(f"✓ Scraped {ref_data['customer_name']} ({ref_data['word_count']} words)")
            
            # Be respectful - wait between requests
            if i < len(urls):
                time.sleep(self.delay)
        
        print(f"\n✓ Scraped {len(references)} references")
        return references


if __name__ == '__main__':
    # Test scraper
    scraper = SnowflakeScraper()
    references = scraper.scrape_all()
    
    # Show sample
    if references:
        print("\nSample reference:")
        sample = references[0]
        print(f"Customer: {sample['customer_name']}")
        print(f"URL: {sample['url']}")
        print(f"Text preview: {sample['raw_text'][:200]}...")
```

## Step 4: Build Claude Classifier

**File: `src/classifiers/claude_classifier.py`**
```python
"""Classifier for customer references using Claude API."""

import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()


class ReferenceClassifier:
    """Classify customer references using Claude."""
    
    def __init__(self):
        """Initialize Claude client."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY in environment")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Load taxonomies
        self.taxonomies = self._load_taxonomies()
    
    def _load_taxonomies(self):
        """Load predefined taxonomies from JSON files."""
        taxonomies = {}
        
        taxonomy_files = ['industries', 'use_cases', 'company_sizes']
        for taxonomy in taxonomy_files:
            path = f'data/taxonomies/{taxonomy}.json'
            if os.path.exists(path):
                with open(path) as f:
                    taxonomies[taxonomy] = json.load(f)
        
        return taxonomies
    
    def classify(self, reference_text, reference_url=""):
        """
        Classify a customer reference.
        
        Args:
            reference_text: Full text of the reference
            reference_url: URL of the reference (for context)
            
        Returns:
            Dict with classification results
        """
        prompt = f"""You are analyzing a customer reference/case study. Extract structured information from the text below.

REFERENCE URL: {reference_url}

REFERENCE TEXT:
{reference_text}

---

Extract the following information and return ONLY valid JSON (no markdown, no explanations):

{{
  "customer_name": "Name of the customer company",
  "industry": "Select ONE from: {', '.join(self.taxonomies.get('industries', {}).get('industries', []))}",
  "company_size": "Select ONE from: {', '.join(self.taxonomies.get('company_sizes', {}).get('company_sizes', []))}",
  "region": "Select ONE: North America, EMEA, APAC, LATAM, or Unknown",
  "country": "Specific country if mentioned, otherwise null",
  "use_cases": ["Select 1-3 relevant from: {', '.join(self.taxonomies.get('use_cases', {}).get('use_cases', []))}"],
  "outcomes": [
    {{
      "type": "performance | cost_savings | revenue_impact | efficiency | other",
      "description": "Brief description of outcome",
      "metric": "Specific metric if mentioned (e.g., '10x faster', '40% reduction')"
    }}
  ],
  "personas": [
    {{
      "title": "Job title of person quoted or featured",
      "name": "Person's name if mentioned",
      "seniority": "C-Level | VP | Director | Manager | Individual Contributor"
    }}
  ],
  "tech_stack": ["List of other technologies mentioned (AWS, Azure, dbt, etc.)"],
  "quoted_text": "Most compelling customer quote from the reference (if any)"
}}

IMPORTANT:
- Use ONLY values from the predefined lists for industry, company_size, use_cases
- If information is not in the text, use "Unknown" or empty array as appropriate
- Keep descriptions concise (1-2 sentences)
- Return ONLY the JSON object, no other text
"""
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Find the JSON content between ```json and ```
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                response_text = response_text[start:end]
            
            classification = json.loads(response_text)
            
            return classification
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse Claude response as JSON: {e}")
            print(f"Response was: {response_text[:500]}")
            return None
        except Exception as e:
            print(f"Classification error: {e}")
            return None


if __name__ == '__main__':
    # Test classifier
    classifier = ReferenceClassifier()
    
    test_text = """
    Capital One Uses Snowflake for Real-Time Fraud Detection
    
    Capital One, one of the largest banks in the United States, implemented Snowflake's
    Data Cloud to power their fraud detection systems. The solution processes millions
    of transactions per day in real-time.
    
    "Snowflake enabled us to analyze transaction patterns 10x faster than our previous
    system," said Sarah Johnson, VP of Data Engineering at Capital One. "We've reduced
    false positives by 40% while catching 25% more fraudulent transactions."
    
    The bank also uses AWS, dbt, and Fivetran alongside Snowflake to build a modern
    data stack that serves 100+ million customers.
    """
    
    result = classifier.classify(test_text, "https://snowflake.com/customers/capital-one")
    print(json.dumps(result, indent=2))
```

## Step 5: Build Orchestration Script

**File: `scripts/test_pipeline.py`**
```python
"""Test the full pipeline: scrape Snowflake → load to Neo4j → classify."""

import sys
sys.path.append('src')

from scrapers.snowflake_scraper import SnowflakeScraper
from graph.neo4j_client import Neo4jClient
from classifiers.claude_classifier import ReferenceClassifier
import json


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
    
    # Save raw data for inspection
    with open('data/scraped/snowflake_raw.json', 'w') as f:
        json.dump(references, f, indent=2)
    print("✓ Saved raw data to data/scraped/snowflake_raw.json")
    
    # Step 2: Load raw data to Neo4j
    print("\n3. Loading raw data to Neo4j...")
    loaded_count = 0
    
    for ref in references:
        try:
            ref_id = db.load_raw_reference('Snowflake', ref)
            loaded_count += 1
            print(f"✓ Loaded {ref['customer_name']} (ID: {ref_id})")
        except Exception as e:
            print(f"✗ Failed to load {ref.get('customer_name', 'Unknown')}: {e}")
    
    print(f"\n✓ Loaded {loaded_count}/{len(references)} references to database")
    
    # Step 3: Classify references
    print("\n4. Classifying references with Claude...")
    
    unclassified = db.get_unclassified_references(limit=100)
    print(f"Found {len(unclassified)} unclassified references")
    
    classified_count = 0
    failed_count = 0
    
    for i, ref in enumerate(unclassified, 1):
        print(f"\n[{i}/{len(unclassified)}] Classifying {ref['url'][:60]}...")
        
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
```

## Step 6: Run the Test
```bash
# Activate virtual environment
source venv/bin/activate

# Run the pipeline
python scripts/test_pipeline.py
```

## Expected Output
```
============================================================
CUSTOMER REFERENCE INTELLIGENCE - TEST PIPELINE
============================================================

1. Initializing components...
✓ Connected to Neo4j
✓ Indexes created

2. Scraping Snowflake customer references...
Fetching customer list from https://www.snowflake.com/en/why-snowflake/customers/
Found 25 customer reference URLs

[1/25]
Scraping: https://www.snowflake.com/customers/capital-one
✓ Scraped Capital One (1842 words)

[2/25]
Scraping: https://www.snowflake.com/customers/netflix
✓ Scraped Netflix (1623 words)

...

✓ Scraped 25 references
✓ Saved raw data to data/scraped/snowflake_raw.json

3. Loading raw data to Neo4j...
✓ Loaded Capital One (ID: abc-123-def)
✓ Loaded Netflix (ID: ghi-456-jkl)
...

✓ Loaded 25/25 references to database

4. Classifying references with Claude...
Found 25 unclassified references

[1/25] Classifying https://www.snowflake.com/customers/capital-one...
✓ Classified as: Capital One | Financial Services | Fraud Detection, Real-time Analytics

[2/25] Classifying https://www.snowflake.com/customers/netflix...
✓ Classified as: Netflix | Media & Entertainment | Real-time Analytics, Recommendation Engines

...

✓ Successfully classified 24/25 references
⚠ Failed to classify 1 references

5. Final Statistics:
============================================================
Total References: 25
Classified References: 24
Total Vendors: 1
Total Customers: 24

✓ Pipeline complete!
```

## Step 7: Validate in Neo4j Browser

Open Neo4j Browser and run these queries:
```cypher
// 1. See all data
MATCH (n)
RETURN n
LIMIT 100

// 2. Count references by industry
MATCH (c:Customer)-[:IN_INDUSTRY]->(i:Industry)
RETURN i.name, count(c) as customer_count
ORDER BY customer_count DESC

// 3. See use cases
MATCH (r:Reference)-[:ADDRESSES_USE_CASE]->(uc:UseCase)
RETURN uc.name, count(r) as ref_count
ORDER BY ref_count DESC

// 4. View a specific customer
MATCH (c:Customer {name: "Capital One"})(uc:UseCase)
MATCH (c)-[:IN_INDUSTRY]->(i:Industry)
RETURN c, r, collect(uc.name) as use_cases, i.name as industry

// 5. Find references about fraud detection
MATCH (r:Reference)-[:ADDRESSES_USE_CASE]->(uc:UseCase {name: "Fraud Detection"})
MATCH (r)-[:FEATURES]->(c:Customer)
RETURN c.name, r.url
```

## Success Criteria Checklist

- [ ] Scraped 20+ Snowflake references
- [ ] All raw text loaded into Neo4j
- [ ] >80% successfully classified by Claude
- [ ] Data queryable in Neo4j Browser
- [ ] Manually reviewed 10 classifications - >80% accurate
- [ ] Can find references by industry, use case, company size

## Troubleshooting

### Scraper Issues

**Problem**: No URLs found
- Check Snowflake's website structure hasn't changed
- Inspect HTML to update CSS selectors
- Try manually visiting the customers page

**Problem**: Scraping fails
- Check internet connection
- Verify you're not being rate-limited (increase delay)
- Check robots.txt compliance

### Database Issues

**Problem**: Connection fails
- Verify AuraDB instance is running
- Check credentials in .env
- Test connection in Neo4j Browser first

**Problem**: Duplicate data
- References should be unique by URL
- Clear database: `MATCH (n) DETACH DELETE n`
- Re-run with fresh data

### Classification Issues

**Problem**: JSON parsing errors
- Claude sometimes returns markdown-wrapped JSON
- Check the response cleaning logic
- Add more robust parsing

**Problem**: Low accuracy
- Tune the classification prompt
- Add more examples
- Adjust taxonomies
- Check if raw text is clean enough

## Next Steps After Success

Once this test pipeline works:

1. Add Databricks scraper (replicate pattern)
2. Add 3-4 more vendors
3. Build similarity search queries
4. Create Streamlit UI
5. Iterate on classification accuracy

## Cost Estimate

- **Neo4j AuraDB Free**: $0 (lifetime free tier)
- **Claude API**: ~$0.50 for 25 references (2,000 tokens avg per reference)
- **Total**: ~$0.50