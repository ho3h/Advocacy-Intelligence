# Customer Reference Intelligence Platform

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

1. **Web Scraper**: Extract customer references from vendor websites (uses HyperBrowser.ai for all scraping)
2. **AI Classifier**: Use Google Gemini to extract structured data from raw reference text
3. **Graph Loader**: Load structured data into Neo4j (AuraDB Free)
4. **Similarity Search**: Find customer references that match a prospect profile
5. **Simple UI**: Streamlit app for searching and exploring data (planned)

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
- **LLM**: Google Gemini API (auto-detects best available model, prefers gemini-2.5-flash)
- **Web Scraping**: HyperBrowser.ai (required for JavaScript-rendered pages)
- **Frontend**: Streamlit (planned)
- **Environment Management**: python-venv with python-dotenv

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

#### Relationships
```cypher(Vendor)-[:PUBLISHED]->(Reference)
(Reference)-[:FEATURES]->(Customer)
(Customer)-[:IN_INDUSTRY]->(Industry)
(Customer)-[:HAS_SIZE]->(CompanySize)
(Reference)-[:ADDRESSES_USE_CASE]->(UseCase)
(Reference)-[:ACHIEVED_OUTCOME]->(Outcome)
(Reference)-[:MENTIONS_PERSONA]->(Persona)
(Customer)-[:USES_TECH]->(Technology)

### Data Flow
Scrape → Raw HTML/Text (HyperBrowser.ai)
Load Raw → Neo4j (with classified=false flag)
Classify → Use Google Gemini to extract structured data
Enrich Graph → Create nodes and relationships from classification
Query → Similarity search, analysis, reporting


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

### Phase 1: Proof of Concept (Weeks 1-2) - IN PROGRESS
- ✅ Scrape Snowflake customer references (paginated discovery, hybrid scraping)
- ✅ Load raw text into AuraDB Free
- ✅ Build Gemini classification function
- ⏳ Validate data quality (manual QA on 20+ classifications)

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

## Repository Structurecustomer-reference-intelligence/
├── README.md
├── PROJECT.md (this file)
├── agents.md (Cursor AI context)
├── requirements.txt
├── .env.example
├── .gitignore
├── src/
│   ├── scrapers/
│   │   ├── init.py
│   │   ├── base_scraper.py
│   │   ├── snowflake_scraper.py
│   │   ├── databricks_scraper.py
│   │   └── ...
│   ├── classifiers/
│   │   ├── init.py
│   │   └── gemini_classifier.py
│   ├── graph/
│   │   ├── init.py
│   │   ├── neo4j_client.py
│   │   ├── schema.py
│   │   └── queries.py
│   ├── ui/
│   │   ├── init.py
│   │   └── streamlit_app.py
│   └── utils/
│       ├── init.py
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

## Environment Variables
```bash
# Neo4j AuraDB
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Google Gemini API
GOOGLE_API_KEY=your-google-api-key

# HyperBrowser.ai (optional - for fallback scraping)
HYPERBROWSER_API_KEY=your-hyperbrowser-api-key

# Optional: for rate limiting
SCRAPE_DELAY_SECONDS=2

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