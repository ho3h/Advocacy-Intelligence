# Advocacy Intelligence Platform

An AI-powered competitive intelligence platform that helps B2B companies discover, analyze, and leverage customer references across their competitive landscape using graph database technology.

## Project Overview

This platform scrapes customer references from competitor websites, classifies them using Google Gemini, stores them in a Neo4j graph database, and enables similarity search to find the best reference matches for sales opportunities.

**Current Phase**: V1 - Proof of Concept  
**Target Industry**: Data/Database companies (Snowflake, Databricks, etc.)

## Features

- **Web Scraping**: HyperBrowser.ai for all scraping (required for JavaScript-rendered pages)
- **Individual File Storage**: Each reference saved as `{customer-slug}-{timestamp}.json` organized by vendor folder
- **AI Classification**: Google Gemini extracts structured data (industries, use cases, outcomes, personas, tech stacks)
- **Graph Database**: Neo4j AuraDB stores relationships between vendors, customers, references, and metadata
- **Similarity Search**: Find customer references matching prospect profiles (industry, use case, company size, region)
- **Idempotent Operations**: Safe to re-run scrapers and classifiers without creating duplicates
- **Dual Storage**: Raw content preserved in both individual files and Neo4j for backup and querying

## Tech Stack

- **Python 3.11+** - Backend language
- **Neo4j AuraDB Free** - Graph database (cloud-hosted Neo4j)
- **Google Gemini API** - Content classification (auto-detects best available model, prefers gemini-2.5-flash)
- **HyperBrowser.ai** - Web scraping service (required for JavaScript-rendered pages)
- **requests** - HTTP library for sitemap fetching
- **python-dotenv** - Environment management

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.9+ works but 3.11+ recommended)
- Neo4j AuraDB Free instance ([sign up here](https://console.neo4j.io/))
- Google API key for Gemini ([get here](https://makersuite.google.com/app/apikey))
- HyperBrowser.ai API key ([required, get here](https://hyperbrowser.ai/))

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
# - HYPERBROWSER_API_KEY (required)
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
│       ├── __init__.py
│       └── file_storage.py   # Individual reference file storage
├── data/
│   ├── taxonomies/          # Classification taxonomies (JSON)
│   │   ├── industries.json
│   │   ├── use_cases.json
│   │   └── company_sizes.json
│   ├── scraped/             # Individual reference files (gitignored)
│   │   └── {vendor}/         # Organized by vendor name
│   │       └── {customer-slug}-{timestamp}.json
│   └── schema/              # Data model definitions
│       └── data_model.json
├── scripts/                 # Orchestration scripts
│   ├── discover_urls.py    # Phase 1: Snowflake URL discovery (pagination)
│   ├── discover_urls_sitemap.py  # Phase 1: Sitemap-based discovery (MongoDB, Redis)
│   ├── discover_urls_redis.py    # Phase 1: Redis URL discovery
│   ├── scrape_phase2.py   # Phase 2: Snowflake content scraping
│   ├── scrape_phase2_mongodb.py  # Phase 2: MongoDB content scraping
│   ├── scrape_phase2_redis.py    # Phase 2: Redis content scraping
│   ├── load_and_classify_mongodb.py  # Phase 3 & 4: MongoDB DB load + classify
│   ├── query_mongodb_data.py    # Sample queries for MongoDB data
│   ├── test_pipeline.py    # Full pipeline: scrape → load → classify
│   └── verify_setup.py     # Verify environment setup
└── docs/
    ├── SCRAPING_PHASES.md   # Detailed phase documentation
    ├── SITEMAP_DISCOVERY.md # Sitemap-based discovery guide
    ├── MONGODB_PIPELINE_SUMMARY.md  # MongoDB pipeline results
    └── MONGODB_DATA_INSIGHTS.md     # Data insights and analytics
```

## How It Works

The platform follows a **4-phase pipeline** for each vendor:

### Phase 1: URL Discovery

**Two approaches available:**

#### Option A: Sitemap-Based Discovery (Preferred - Fast & Free!)
- **Method**: Parse website sitemaps to extract customer reference URLs
- **Speed**: ~10 seconds vs. hours with pagination
- **Cost**: $0 (free!)
- **Works for**: MongoDB, most modern websites
- **Script**: `scripts/discover_urls_sitemap.py`

```bash
python scripts/discover_urls_sitemap.py mongodb
```

#### Option B: Pagination-Based Discovery (Fallback)
- **Method**: Iterate through paginated listing pages
- **Speed**: Minutes to hours (depends on pages)
- **Cost**: HyperBrowser.ai costs (~$0.01-0.05 per page)
- **Works for**: Redis (Cloudflare protection), Snowflake
- **Script**: `scripts/discover_urls.py` or `scripts/discover_urls_redis.py`

**Output**: List of unique customer reference URLs saved to `data/scraped/{vendor}/discovered_urls-{timestamp}.json`

### Phase 2: Content Scraping

**Process**:
- Uses **HyperBrowser.ai** for all scraping (required for JavaScript-rendered pages)
- Fetches each reference URL and extracts content
- Prefers markdown format, falls back to HTML
- Filters low-quality scrapes (<100 words)
- Rate limiting: 2-second delays between requests

**Output**: Individual JSON files saved to `data/scraped/{vendor}/{customer-slug}-{timestamp}.json`

**Scripts**:
- `scripts/scrape_phase2.py` - Snowflake
- `scripts/scrape_phase2_mongodb.py` - MongoDB
- `scripts/scrape_phase2_redis.py` - Redis

### Phase 3: Database Loading

**Process**:
- Loads scraped references from files into Neo4j
- Creates Reference nodes with raw text
- Links to Vendor nodes
- URL deduplication (safe to re-run)
- Sets `classified=false` flag

**Output**: Reference nodes in Neo4j ready for classification

**Scripts**:
- `scripts/load_and_classify_mongodb.py` - MongoDB (includes classification)
- `scripts/test_pipeline.py` - Snowflake (full pipeline)

### Phase 4: Classification

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
- Updates graph with relationships (Customer, Industry, UseCase, Outcome, etc.)

**Output**: Fully classified and enriched graph data ready for similarity search

### Complete Workflow Example

```bash
# MongoDB (using sitemap - fastest!)
python scripts/discover_urls_sitemap.py mongodb      # Phase 1: ~10 seconds
python scripts/scrape_phase2_mongodb.py              # Phase 2: ~36 minutes
python scripts/load_and_classify_mongodb.py          # Phase 3 & 4: ~47 minutes

# Snowflake (using pagination)
python scripts/discover_urls.py                      # Phase 1: ~5-15 minutes
python scripts/scrape_phase2.py                      # Phase 2: ~30-60 minutes
python scripts/test_pipeline.py                      # Phase 3 & 4: ~10-20 minutes
```

### Graph Storage

**Neo4j Graph Structure**:

```mermaid
erDiagram
    Vendor ||--o{ Reference : PUBLISHED
    Reference ||--|| Customer : FEATURES
    Customer }o--|| Industry : IN_INDUSTRY
    Reference }o--o{ UseCase : ADDRESSES_USE_CASE
    Reference }o--o{ Outcome : ACHIEVED_OUTCOME
    Reference }o--o{ Persona : MENTIONS_PERSONA
    Reference }o--o{ Technology : MENTIONS_TECH

    Vendor {
        string name PK
        string website
    }
    
    Reference {
        string id PK
        string url
        string raw_text
        integer word_count
        datetime scraped_date
        datetime classification_date
        string quoted_text
        boolean classified
    }
    
    Customer {
        string name PK
        string size
        string region
        string country
    }
    
    Industry {
        string name PK
    }
    
    UseCase {
        string name PK
    }
    
    Persona {
        string title PK
        string name
        string seniority
    }
    
    Outcome {
        string description PK
        string type
        string metric
    }
    
    Technology {
        string name PK
    }
```

**Key Features**:
- Idempotent operations (MERGE, not CREATE)
- Raw text preserved in Reference nodes
- `classified` flag tracks processing status
- Indexes on Customer.name, Reference.url, Vendor.name
- Full data model available in `data/schema/data_model.json`

**Node Descriptions**:
- **Vendor**: Company publishing the reference (e.g., Snowflake)
- **Reference**: The actual case study/video/blog content with raw scraped text
- **Customer**: The company being featured in the reference
- **Industry**: Industry classification (Financial Services, Technology, etc.)
- **UseCase**: Use cases addressed (ML/AI, Data Lakehouse, etc.)
- **Outcome**: Business outcomes achieved (performance, cost savings, etc.)
- **Persona**: Job titles and personas featured in the reference
- **Technology**: Technologies mentioned (AWS, dbt, etc.)

## Usage Examples

### MongoDB Pipeline (Recommended - Uses Sitemap)

```bash
# Phase 1: Discover URLs via sitemap (~10 seconds, free!)
python scripts/discover_urls_sitemap.py mongodb

# Phase 2: Scrape content (~36 minutes, ~$5-12)
python scripts/scrape_phase2_mongodb.py

# Phase 3 & 4: Load to Neo4j and classify (~47 minutes, ~$0.23-2.34)
python scripts/load_and_classify_mongodb.py
```

**Result**: 234 MongoDB references scraped, loaded, and classified!

### Snowflake Pipeline (Pagination-Based)

```bash
# Phase 1: Discover URLs via pagination (~5-15 minutes)
python scripts/discover_urls.py

# Phase 2: Scrape content (~30-60 minutes)
python scripts/scrape_phase2.py

# Full pipeline (includes Phase 3 & 4)
python scripts/test_pipeline.py
```

### Redis Pipeline

```bash
# Phase 1: Discover URLs (uses HyperBrowser.ai due to Cloudflare)
python scripts/discover_urls_redis.py

# Phase 2: Scrape content
python scripts/scrape_phase2_redis.py
```

**File Storage**: Each reference is automatically saved as `{customer-slug}-{timestamp}.json` in `data/scraped/{vendor}/`. This enables:
- Local backups of all scraped content
- Easy export to cloud storage (S3, GCS, etc.)
- Version control of individual stories
- Incremental updates without re-scraping everything

To disable file saving, set `SAVE_RAW_DATA=false` in your environment.

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
- `SAVE_RAW_DATA` - Save individual reference files (default: true, set to false to disable)

### Scraper Configuration

In `src/scrapers/snowflake_scraper.py`:
- `delay` - Seconds between requests (default: 2)
- `use_hyperbrowser_fallback` - Enable/disable HyperBrowser.ai fallback (default: True)
- `max_pages` - Maximum paginated pages to scrape (default: 5)

## Current Status

### Working Features

✅ **URL Discovery**:
- **Sitemap-based discovery** (MongoDB, fast & free!)
- Paginated URL discovery (Snowflake, Redis)
- Automatic completion detection
- URL filtering and deduplication

✅ **Content Scraping**:
- HyperBrowser.ai for all page fetching
- Cloudflare bypass via HyperBrowser.ai
- Quality filtering (<100 words skipped)
- Individual file storage (organized by vendor)

✅ **Classification**:
- Google Gemini integration (auto-detects best model)
- Structured data extraction
- Taxonomy-driven classification
- 100% success rate on MongoDB (234/234)

✅ **Database**:
- Neo4j connection and operations
- Idempotent data loading
- Graph relationship creation
- Statistics queries

✅ **Vendors Supported**:
- **MongoDB**: 234 references (sitemap-based discovery)
- **Snowflake**: 18 references (pagination-based)
- **Redis**: 8 references discovered (pagination-based)

### Current Data

- **Total References**: 252 (234 MongoDB + 18 Snowflake)
- **Total Customers**: 243 unique customers
- **Total Use Cases**: 47 different use cases
- **Total Industries**: 21 industries
- **Total Outcomes**: 885 outcome records with metrics

See `docs/MONGODB_DATA_INSIGHTS.md` for detailed analytics.

## Cost Estimates

- **Neo4j AuraDB Free**: $0 (lifetime free tier)
- **Google Gemini**: ~$0.001-0.01 per classification (gemini-2.5-flash is very affordable)
- **HyperBrowser.ai**: ~$0.01-0.05 per page (required for all scraping)
- **Total for 100 references**: ~$1-5 (mostly HyperBrowser.ai costs)

## Troubleshooting

### Scraper Issues

**Problem**: No URLs found
- Check if Snowflake's page structure changed
- Verify HyperBrowser.ai API key is set (required)
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
- Shouldn't happen with MERGE operations (URL deduplication built-in)
- Use cleanup script: `python scripts/cleanup_duplicates.py --all`
- Clear database: `MATCH (n) DETACH DELETE n` (use with caution)

### File Storage Issues

**Problem**: Files not being saved
- Check `SAVE_RAW_DATA` environment variable (default: true)
- Verify write permissions on `data/scraped/` directory
- Check disk space

**Problem**: Want to export files to cloud storage
- Files are organized by vendor: `data/scraped/{vendor}/`
- Easy to sync with `aws s3 sync`, `gsutil`, or `rclone`
- Each file is self-contained JSON with all reference data

## Development Roadmap

### Phase 1: Proof of Concept ✅ (Complete)
- ✅ Project structure
- ✅ Snowflake scraper with pagination
- ✅ MongoDB scraper with sitemap discovery
- ✅ Redis scraper (pagination)
- ✅ Sitemap-based URL discovery utility
- ✅ Individual file storage (organized by vendor)
- ✅ Gemini classifier
- ✅ Neo4j integration
- ✅ URL deduplication and quality filtering
- ✅ 234 MongoDB references fully processed
- ✅ Data exploration and insights

### Phase 2: Core Platform (Next)
- ⏳ Build similarity search queries
- ⏳ Create basic Streamlit UI
- ⏳ Add Databricks scraper (try sitemap first!)
- ⏳ Refine classification prompts (improve "Unknown" classifications)
- ⏳ Add more vendors using sitemap approach

### Phase 3: Scale & Polish
- Add 5+ more vendors
- Advanced filtering and browsing
- User testing
- Production deployment

## Contributing

This is currently a private project. For questions or suggestions, please contact the project maintainer.

## License

TBD - Private/Proprietary for now

## Author

Theo - Neo4j Customer Marketing
