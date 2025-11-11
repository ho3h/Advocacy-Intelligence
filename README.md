# Advocacy Intelligence Platform

An AI-powered competitive intelligence platform that helps B2B companies discover, analyze, and leverage customer references across their competitive landscape using graph database technology.

## Project Overview

This platform scrapes customer references from competitor websites, classifies them using Google Gemini, stores them in a Neo4j graph database, and enables similarity search to find the best reference matches for sales opportunities.

**Current Phase**: V1 - Proof of Concept  
**Target Industry**: Data/Database companies (Snowflake, Databricks, etc.)

## Features

- **Web Scraping**: HyperBrowser.ai for JavaScript-rendered pages (BeautifulSoup always gets blocked by Cloudflare)
- **AI Classification**: Google Gemini extracts structured data (industries, use cases, outcomes, personas, tech stacks)
- **Graph Database**: Neo4j AuraDB stores relationships between vendors, customers, references, and metadata
- **Similarity Search**: Find customer references matching prospect profiles (industry, use case, company size, region)
- **Idempotent Operations**: Safe to re-run scrapers and classifiers without creating duplicates

## Tech Stack

- **Python 3.11+** - Backend language
- **Neo4j AuraDB Free** - Graph database (cloud-hosted Neo4j)
- **Google Gemini API** - Content classification (auto-detects best available model)
- **BeautifulSoup4** - Primary web scraping (free, fast)
- **HyperBrowser.ai** - Fallback scraper for protected/JavaScript pages (optional)
- **python-dotenv** - Environment management

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.9+ works but 3.11+ recommended)
- Neo4j AuraDB Free instance ([sign up here](https://console.neo4j.io/))
- Google API key for Gemini ([get here](https://makersuite.google.com/app/apikey))
- HyperBrowser.ai API key ([optional, get here](https://hypeHyperBrowser.airbrowser.ai/))

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Advocacy-Intelligence
```

2. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your credentials:
# - NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
# - GOOGLE_API_KEY
# - HYPERBROWSER_API_KEY (optional but recommended)
```

5. **Verify setup:**
```bash
python scripts/verify_setup.py
```

6. **Run the test pipeline:**
```bash
python scripts/test_pipeline.py
```

## Project Structure

```
Advocacy-Intelligence/
├── README.md                 # This file
├── PROJECT.md                # Comprehensive project documentation
├── agents.md                 # AI assistant context
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── src/
│   ├── scrapers/            # Web scraping modules
│   │   ├── __init__.py
│   │   └── snowflake_scraper.py  # Snowflake customer reference scraper
│   ├── classifiers/         # LLM classification modules
│   │   ├── __init__.py
│   │   └── gemini_classifier.py  # Google Gemini classifier
│   ├── graph/               # Neo4j database client
│   │   ├── __init__.py
│   │   └── neo4j_client.py  # Database operations
│   └── utils/               # Utility functions
│       └── __init__.py
├── data/
│   ├── taxonomies/          # Classification taxonomies (JSON)
│   │   ├── industries.json
│   │   ├── use_cases.json
│   │   └── company_sizes.json
│   └── scraped/             # Raw scraped data (gitignored)
├── scripts/                 # Orchestration scripts
│   ├── test_pipeline.py    # Full pipeline: scrape → load → classify
│   └── verify_setup.py     # Verify environment setup
└── docs/
    └── HYBRID_SCRAPER.md    # Scraper documentation
```

## How It Works

### 1. Scraping Phase

The scraper uses **HyperBrowser.ai directly**:

- BeautifulSoup always gets blocked by Cloudflare, so we skip it entirely
- HyperBrowser.ai handles JavaScript rendering and bypasses anti-bot protection
- All case study and video pages require JavaScript to load content

**Snowflake Scraper**:
- Discovers case study URLs from paginated listing pages: `/en/customers/all-customers/?page=0&pageSize=12&offset=0`
- Extracts case study links matching pattern: `/customers/all-customers/case-study/{company}/`
- Handles pagination automatically
- Respects rate limits (2-second delays)

### 2. Classification Phase

**Google Gemini Classifier**:
- Auto-detects best available model (prefers `gemini-2.5-flash` for speed/cost)
- Extracts structured data:
  - Customer name, industry, company size, region
  - Use cases (1-3 per reference)
  - Business outcomes (performance, cost savings, etc.)
  - Personas (job titles, seniority)
  - Tech stack mentions
  - Best customer quote
- Uses predefined taxonomies for consistency
- Handles rate limits with exponential backoff

### 3. Graph Storage

**Neo4j Graph Structure**:
```
(Vendor)-[:PUBLISHED]->(Reference)
(Reference)-[:FEATURES]->(Customer)
(Customer)-[:IN_INDUSTRY]->(Industry)
(Reference)-[:ADDRESSES_USE_CASE]->(UseCase)
(Reference)-[:ACHIEVED_OUTCOME]->(Outcome)
(Reference)-[:MENTIONS_PERSONA]->(Persona)
(Reference)-[:MENTIONS_TECH]->(Technology)
```

**Key Features**:
- Idempotent operations (MERGE, not CREATE)
- Raw text preserved in Reference nodes
- `classified` flag tracks processing status
- Indexes on Customer.name, Reference.url, Vendor.name

## Usage Examples

### Run Full Pipeline

```bash
python scripts/test_pipeline.py
```

This will:
1. Scrape Snowflake customer references (currently limited to 3 pages, ~25 case studies)
2. Load raw data into Neo4j
3. Classify references with Gemini
4. Display statistics

### Test Single Page Scraping

```bash
python scripts/test_single_page.py
```

### Verify Setup

```bash
python scripts/verify_setup.py
```

### Query Neo4j Browser

Access Neo4j Browser from your AuraDB console and run queries like:

```cypher
// Count references by industry
MATCH (c:Customer)-[:IN_INDUSTRY]->(i:Industry)
RETURN i.name, count(c) as customer_count
ORDER BY customer_count DESC

// Find references about fraud detection
MATCH (r:Reference)-[:ADDRESSES_USE_CASE]->(uc:UseCase {name: "Fraud Detection"})
MATCH (r)-[:FEATURES]->(c:Customer)
RETURN c.name, r.url

// View a specific customer's data
MATCH (c:Customer {name: "Red Sea Global"})<-[:FEATURES]-(r:Reference)
MATCH (r)-[:ADDRESSES_USE_CASE]->(uc:UseCase)
RETURN c, r, collect(uc.name) as use_cases
```

## Configuration

### Environment Variables

Required:
- `NEO4J_URI` - Neo4j AuraDB connection URI (e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
- `NEO4J_USERNAME` - Usually `neo4j`
- `NEO4J_PASSWORD` - Your AuraDB password
- `GOOGLE_API_KEY` - Google Gemini API key

Optional:
- `HYPERBROWSER_API_KEY` - For fallback scraping (highly recommended)
- `SCRAPE_DELAY_SECONDS` - Delay between requests (default: 2)

### Scraper Configuration

In `src/scrapers/snowflake_scraper.py`:
- `delay` - Seconds between requests (default: 2)
- `use_hyperbrowser_fallback` - Enable/disable HyperBrowser.ai fallback (default: True)
- `max_pages` - Maximum paginated pages to scrape (default: 5)

## Current Status

### Working Features

✅ **Scraping**:
- Paginated URL discovery from `/en/customers/all-customers/`
- Case study URL extraction
- Hybrid BeautifulSoup + HyperBrowser.ai scraping
- Cloudflare bypass via HyperBrowser.ai

✅ **Classification**:
- Google Gemini integration
- Auto model detection
- Structured data extraction
- Taxonomy-driven classification

✅ **Database**:
- Neo4j connection and operations
- Idempotent data loading
- Graph relationship creation
- Statistics queries

### Known Limitations

- Currently limited to Snowflake (Databricks and others coming)
- Pagination limited to 5 pages (~60 case studies) for testing
- Some pages return short content (may need content extraction tuning)
- Customer name extraction could be improved

## Cost Estimates

- **Neo4j AuraDB Free**: $0 (lifetime free tier)
- **Google Gemini**: ~$0.001-0.01 per classification (gemini-2.5-flash is very affordable)
- **HyperBrowser.ai**: ~$0.01-0.05 per page (only used when BeautifulSoup fails)
- **Total for 100 references**: ~$1-5 (mostly HyperBrowser.ai costs)

## Troubleshooting

### Scraper Issues

**Problem**: No URLs found
- Check if Snowflake's page structure changed
- Verify HyperBrowser.ai API key is set (required - BeautifulSoup doesn't work)
- Try manually visiting the paginated URL

**Problem**: Content too short (~50 words)
- This means HyperBrowser.ai didn't get full content
- Check HyperBrowser.ai API key is valid and has credits
- Some pages may need different scraping configuration

### Classification Issues

**Problem**: Classification returns None
- Check Google API key is valid
- Verify you have API quota available
- Check Gemini model availability in your region

**Problem**: Low accuracy
- Review taxonomies in `data/taxonomies/`
- Tune prompts in `src/classifiers/gemini_classifier.py`
- Manually QA classifications and adjust

### Database Issues

**Problem**: Connection fails
- Verify AuraDB instance is running
- Check credentials in `.env`
- Test connection in Neo4j Browser first

**Problem**: Duplicate nodes
- Shouldn't happen with MERGE operations
- Clear database: `MATCH (n) DETACH DELETE n`
- Re-run pipeline

## Development Roadmap

### Phase 1: Proof of Concept (Current)
- ✅ Project structure
- ✅ Snowflake scraper with pagination
- ✅ Gemini classifier
- ✅ Neo4j integration
- ⏳ Data quality validation

### Phase 2: Core Platform (Next)
- Add Databricks scraper
- Refine classification prompts
- Build similarity search queries
- Create basic Streamlit UI

### Phase 3: Scale & Polish
- Add 5+ more vendors
- Advanced filtering and browsing
- User testing
- Documentation

## Contributing

This is currently a private project. For questions or suggestions, please contact the project maintainer.

## License

TBD - Private/Proprietary for now

## Author

Theo - Neo4j Customer Marketing
