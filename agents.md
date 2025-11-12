# AI Agent Instructions for Customer Reference Intelligence Platform

This file provides context for AI coding assistants (like Cursor) working on this project.

## Project Overview

This is a competitive intelligence platform for B2B customer marketing teams. We scrape customer references from company websites, classify them using LLMs, store them in a Neo4j graph database, and enable similarity search to find the best reference matches for sales opportunities.

**Current Phase**: V1 - Proof of Concept
**Target Industry**: Data/Database companies (Snowflake, Databricks, etc.)

## Key Technical Context

### Tech Stack
- **Python 3.11+** for all backend code
- **Neo4j AuraDB Free** for graph storage (cloud-hosted Neo4j)
- **Google Gemini API** (auto-detects best available model, prefers gemini-2.5-flash) for content classification
- **HyperBrowser.ai** for web scraping (required for JavaScript-rendered pages)
- **requests** for sitemap fetching (sitemap-based discovery)
- **Streamlit** for UI (later phase)
- **python-dotenv** for environment management

### Critical Design Patterns

#### 1. Separation of Concerns - 4-Phase Pipeline
```
Phase 1: URL Discovery → Phase 2: Content Scraping → Phase 3: Database Loading → Phase 4: Classification
```

**Phase 1: URL Discovery**
- **Option A (Preferred)**: Sitemap-based discovery (`scripts/discover_urls_sitemap.py`)
  - Fast (~10 seconds), free, works for MongoDB and most modern sites
  - Parses sitemap XML, filters for customer URLs using regex patterns
- **Option B (Fallback)**: Pagination-based discovery (`scripts/discover_urls.py`)
  - Slower (minutes-hours), costs HyperBrowser.ai, needed for Cloudflare-protected sites
  - Uses flexible pagination system from `scrapers.pagination`
- **Output**: List of URLs saved to `data/scraped/{vendor}/discovered_urls-{timestamp}.json`

**Phase 2: Content Scraping**
- Loads URLs from Phase 1 output files
- Uses HyperBrowser.ai for all page fetching (required for JavaScript)
- Saves each reference as individual JSON file: `data/scraped/{vendor}/{customer-slug}-{timestamp}.json`
- Filters low-quality scrapes (<100 words)
- **Scripts**: `scripts/scrape_phase2.py`, `scripts/scrape_phase2_mongodb.py`, etc.

**Phase 3: Database Loading**
- Loads scraped references from files into Neo4j
- Creates Reference nodes with raw text
- Links to Vendor nodes
- Sets `classified=false` flag
- URL deduplication (idempotent)

**Phase 4: Classification**
- Queries database for `classified=false` references
- Uses Gemini to extract structured data
- Updates graph with Customer, Industry, UseCase, Outcome, Persona, Technology nodes
- Sets `classified=true` when complete

Each phase is separate and can be run independently. Raw content is always preserved:
- **Individual files**: Each reference saved as `data/scraped/{vendor}/{customer-slug}-{timestamp}.json`
- **Database**: Raw text stored in Neo4j Reference nodes
- **Backup**: Files serve as local backup and enable easy export to cloud storage

#### 2. Idempotent Graph Operations
Always use MERGE, never CREATE for nodes that might already exist:
```python✅ GOOD - Won't create duplicates
session.run("""
MERGE (c:Customer {name: $name})
SET c.size = $size
""", params)❌ BAD - Creates duplicates on re-run
session.run("""
CREATE (c:Customer {name: $name, size: $size})
""", params)

#### 3. Processing Flags
References have a `classified` boolean property:
- `classified=false` means raw text needs classification
- After classification completes, set `classified=true`
- This lets us reprocess if we improve classification prompts

#### 4. Error Handling for External APIs
Always handle rate limits and network errors:
```pythonimport time
import google.generativeai as genai

def classify_with_retry(text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return model.generate_content(...)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():  # Rate limit
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            print(f"API error: {e}")
            raise

#### 5. Schema Consistency
Use the predefined taxonomies in `data/taxonomies/` for classification:
- `industries.json` - Industry categories
- `use_cases.json` - Use case types
- `company_sizes.json` - Company size bands

Load these into prompts to ensure consistent classification.

## Graph Schema

The complete data model is defined in `data/schema/data_model.json` and can be validated using Neo4j data modeling MCP tools.

### Data Model Diagram

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

### Core Nodes

**Vendor** - Company publishing the reference
- `name` (PK): Vendor name (e.g., "Snowflake")
- `website`: Vendor website URL

**Reference** - The actual case study/video/blog content
- `id` (PK): Unique reference ID (UUID)
- `url`: Source URL
- `raw_text`: Full scraped text content
- `word_count`: Number of words in raw_text
- `scraped_date`: When content was scraped
- `classification_date`: When classification completed
- `quoted_text`: Best customer quote extracted
- `classified`: Processing flag (false = needs classification)

**Customer** - Company featured in the reference
- `name` (PK): Customer company name (e.g., "Capital One")
- `size`: Company size (Enterprise, Mid-Market, SMB, Startup, Unknown)
- `region`: Geographic region (North America, EMEA, APAC, LATAM, Unknown)
- `country`: Specific country if mentioned (optional)

**Industry** - Industry classification
- `name` (PK): Industry name (e.g., "Financial Services", "Technology & Software")

**UseCase** - Use cases addressed
- `name` (PK): Use case name (e.g., "ML/AI & Predictive Analytics", "Data Lakehouse")

**Persona** - Job titles/personas featured
- `title` (PK): Job title (e.g., "Chief Data Officer")
- `name`: Person's name if mentioned
- `seniority`: Seniority level (C-Level, VP, Director, Manager, Individual Contributor)

**Outcome** - Business outcomes achieved
- `description` (PK): Outcome description (e.g., "10x faster queries")
- `type`: Outcome type (performance, cost_savings, revenue_impact, efficiency, other)
- `metric`: Specific metric if mentioned (e.g., "10x", "40% reduction")

**Technology** - Technologies mentioned
- `name` (PK): Technology name (e.g., "AWS", "dbt", "PostgreSQL")

### Core Relationships

```cypher
(Vendor)-[:PUBLISHED]->(Reference)
(Reference)-[:FEATURES]->(Customer)
(Customer)-[:IN_INDUSTRY]->(Industry)
(Reference)-[:ADDRESSES_USE_CASE]->(UseCase)
(Reference)-[:ACHIEVED_OUTCOME]->(Outcome)
(Reference)-[:MENTIONS_PERSONA]->(Persona)
(Reference)-[:MENTIONS_TECH]->(Technology)
```

### Indexes

- `Customer.name` - For fast customer lookups
- `Reference.url` - For URL deduplication
- `Vendor.name` - For vendor lookups

## Common Tasks & How to Approach Them

### Task: Add a New Scraper

**IMPORTANT: Always try sitemap first!** It's 100x faster and free.

1. **Check if vendor has sitemap:**
   ```bash
   curl -I https://vendor.com/sitemap.xml
   ```

2. **If sitemap exists:**
   - Add vendor config to `src/utils/sitemap_discovery.py` → `VENDOR_CONFIGS`
   - Test: `python scripts/discover_urls_sitemap.py {vendor}`
   - If it works, you're done with Phase 1! (10 seconds vs. hours)

3. **If no sitemap or Cloudflare blocks it:**
   - Create scraper file: `src/scrapers/{vendor}_scraper.py`
   - Follow pattern from `mongodb_scraper.py` or `redis_scraper.py`
   - **Use flexible pagination system**: Import from `scrapers.pagination`:
     - `OffsetPaginationStrategy` - For offset-based pagination (Snowflake style)
     - `PageNumberPaginationStrategy` - For simple page numbers
     - `PathPaginationStrategy` - For path-based pagination
   - Implement these methods:
     - `get_customer_reference_urls()` - Uses `paginate_with_strategy()` OR sitemap discovery
     - `scrape_reference(url)` - Returns dict with raw_text, customer_name, metadata
   - Add rate limiting (2-3 second delays)
   - Use HyperBrowser.ai for all page fetching (required for JavaScript)

4. **Create Phase 2 script:**
   - Copy `scripts/scrape_phase2_mongodb.py` as template
   - Update vendor name and file paths
   - Handles resume capability (skips already-scraped URLs)

5. **Create Phase 3 & 4 script:**
   - Copy `scripts/load_and_classify_mongodb.py` as template
   - Updates vendor name

**Return schema**:
```python{
'url': str,
'raw_text': str,
'raw_html': str,  # optional
'customer_name': str,  # if obvious from URL/title
'scraped_date': str,  # ISO format
'word_count': int
}
```

**File Storage**: The pipeline automatically saves each reference to `data/scraped/{vendor}/{customer-slug}-{timestamp}.json` using `utils.file_storage.save_reference_file()`. This provides:
- Local backup of all scraped content
- Easy export to cloud storage (S3, GCS, etc.)
- Version control of individual stories
- Incremental updates without re-scraping

To disable file saving, set `SAVE_RAW_DATA=false` in environment variables.

### Task: Improve Classification Prompt

1. Edit `src/classifiers/gemini_classifier.py` (prompts are inline in the `classify` method)
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
```cypherCREATE INDEX customer_name IF NOT EXISTS FOR (c:Customer) ON (c.name)
CREATE INDEX reference_url IF NOT EXISTS FOR (r:Reference) ON (r.url)

### Task: Debug Graph Data

**Preferred Method: Use Neo4j MCP Tools**

Always use the Neo4j Cypher MCP tools (`mcp_neo4j-database_read_neo4j_cypher` and `mcp_neo4j-database_write_neo4j_cypher`) for querying the database. These tools provide direct access without needing to write Python code.

**For read queries:**
- Use `mcp_neo4j-database_read_neo4j_cypher` for SELECT/MATCH queries
- Returns results as structured data
- No need to manage Neo4j client connections

**For write queries:**
- Use `mcp_neo4j-database_write_neo4j_cypher` for CREATE/UPDATE/DELETE operations
- Use with caution - prefer idempotent operations

**For schema inspection:**
- Use `mcp_neo4j-database_get_neo4j_schema` to understand the current database structure
- Helps verify data model matches expectations

**For data modeling:**
- Use `mcp_neo4j-data-modeling_*` tools for validating and managing data models
- Useful when adding new node types or relationships

**Example queries using MCP:**
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
MATCH (c:Customer {name: "Capital One"})<-[:FEATURES]-(r:Reference)
MATCH (r)-[:ADDRESSES_USE_CASE]->(uc:UseCase)
RETURN c, r, collect(uc.name) as use_cases
```

**Alternative: Neo4j Browser** (accessible from AuraDB console)
- Use for visual exploration and ad-hoc queries
- Good for manual inspection and debugging
- Not suitable for automated queries or scripts

## Common Pitfalls to Avoid

### 1. Don't Create Duplicate Nodes
Always use MERGE with a unique property (usually `name` or `id`)

### 2. Don't Store Secrets in Code
Use environment variables loaded from `.env`:
```pythonfrom dotenv import load_dotenv
import osload_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

### 3. Don't Scrape Too Fast
Always add delays between requests (2-3 seconds minimum):
```pythonimport timefor url in urls:
data = scrape_url(url)
time.sleep(2)  # Be respectful

### 4. Don't Assume HTML Structure
Websites change. Always:
- Check if elements exist before accessing
- Use try/except for parsing
- Log when expected elements are missing
```pythontry:
customer_name = soup.find('h1', class_='customer-name').text.strip()
except AttributeError:
print(f"Could not find customer name at {url}")
customer_name = "Unknown"

### 5. Don't Ignore API Costs
Google Gemini (gemini-2.5-flash) is very affordable. For v1:
- ~100-200 references to classify
- ~$0.001-0.01 per classification (gemini-2.5-flash is very cost-effective)
- HyperBrowser.ai: ~$0.01-0.05 per page (required for all scraping)
- Total cost: ~$1-5 for v1 dataset (mostly HyperBrowser.ai costs)

Track usage during development.

### 6. Preserve Raw Data in Multiple Formats
Raw scraped content is preserved in two places:
- **Individual JSON files**: `data/scraped/{vendor}/{customer-slug}-{timestamp}.json` - Easy to backup, version, and export
- **Neo4j database**: `Reference.raw_text` property - Queryable, searchable, always available

This dual storage approach ensures:
- Files can be easily pushed to cloud storage or versioned separately
- Database provides fast querying and relationship traversal
- If one storage fails, the other serves as backup

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
- `*_filepath` for file paths

## Testing Approach

For v1, keep testing simple:

1. **Manual QA**: Inspect 10-20 scraped references in Neo4j Browser
2. **Classification accuracy**: Manually review 20 classifications vs source material
3. **Query correctness**: Run similarity search on known examples, verify results make sense
4. **End-to-end**: Scrape vendor → Classify → Query → Visual inspection

Automated tests can come in v2.

## Database Query Best Practices

### Always Use Neo4j MCP Tools

When querying the Neo4j database, **always prefer MCP tools** over writing Python code:

1. **For read queries**: Use `mcp_neo4j-database_read_neo4j_cypher`
   - Direct Cypher query execution
   - Returns structured results
   - No connection management needed

2. **For schema inspection**: Use `mcp_neo4j-database_get_neo4j_schema`
   - Understand current database structure
   - Check node counts and relationships
   - Verify indexes exist

3. **For data modeling**: Use `mcp_neo4j-data-modeling_*` tools
   - Validate data models before implementation
   - Export/import data models
   - Generate Cypher queries for ingestion

4. **For write operations**: Use `mcp_neo4j-database_write_neo4j_cypher` sparingly
   - Prefer idempotent operations (MERGE over CREATE)
   - Use Python Neo4jClient for complex multi-step operations

**Example workflow:**
1. Use `get_neo4j_schema` to understand current structure
2. Use `read_neo4j_cypher` to query data
3. Use `write_neo4j_cypher` only for simple updates
4. Use Python `Neo4jClient` for complex classification updates

## When to Ask for Help

If you encounter:
- Websites with heavy JavaScript or Cloudflare protection (use HyperBrowser.ai fallback)
- Gemini API rate limits that can't be solved with exponential backoff
- Neo4j query performance issues
- Classification accuracy below 80% after prompt tuning
- Data model questions (e.g., should this be a node or property?)
- Outcome nodes with null metrics (ensure metric is always a string, even if empty)
- MCP tool connection issues (check Neo4j credentials in environment)

Flag it and ask rather than guessing.

## Current Sprint Focus

**Phase 1: Proof of Concept** ✅ (Complete!)

Tasks:
1. ✅ Set up project structure
2. ✅ Build Snowflake scraper (with pagination and HyperBrowser.ai)
3. ✅ Build MongoDB scraper (with sitemap discovery - 10 seconds!)
4. ✅ Build Redis scraper (with pagination)
5. ✅ Create sitemap-based URL discovery utility
6. ✅ Load raw data to AuraDB
7. ✅ Create Gemini classification function
8. ✅ Process 234 MongoDB references end-to-end
9. ✅ Data exploration and insights

**Current Status**:
- **MongoDB**: 234 references fully processed (sitemap discovery worked perfectly!)
- **Snowflake**: 18 references processed
- **Redis**: 8 URLs discovered (ready for Phase 2)

**Next Steps**:
- Build similarity search queries
- Add Databricks (try sitemap first!)
- Create Streamlit UI
- Improve classification accuracy (fix "Unknown" industries/regions)

## Useful Neo4j Cypher Patterns

### Loading raw data
```cypherMERGE (v:Vendor {name: $vendor_name})
CREATE (r:Reference {
id: randomUUID(),
url: $url,
raw_text: $raw_text,
scraped_date: datetime(),
classified: false
})
MERGE (v)-[:PUBLISHED]->(r)
RETURN r.id

### Classification update
```cypherMATCH (r:Reference {id: $ref_id})
SET r.classified = true,
r.classification_date = datetime(),
r.quoted_text = $quoted_textWITH r
MERGE (c:Customer {name: $customer_name})
SET c.size = $size, c.region = $region
MERGE (r)-[:FEATURES]->(c)WITH r, c
MERGE (i:Industry {name: $industry})
MERGE (c)-[:IN_INDUSTRY]->(i)WITH r
UNWIND $use_cases as uc_name
MERGE (uc:UseCase {name: uc_name})
MERGE (r)-[:ADDRESSES_USE_CASE]->(uc)

### Similarity search skeleton
```cypher// Given a prospect profile, find similar customers
MATCH (c:Customer)-[:IN_INDUSTRY]->(i:Industry {name: $industry})
WHERE c.region = $region AND c.size = $sizeMATCH (c)<-[:FEATURES]-(r:Reference)-[:ADDRESSES_USE_CASE]->(uc:UseCase)
WHERE uc.name IN $use_casesRETURN c, count(DISTINCT r) as ref_count, collect(DISTINCT uc.name) as matching_use_cases
ORDER BY ref_count DESC
LIMIT 10

## Remember

- **Start simple**: Get one vendor working end-to-end before scaling
- **Preserve raw data**: Always keep original scraped text
- **Iterate on prompts**: Classification will improve with tuning
- **Use the graph**: When queries get complex, the graph relationships make them simple
- **Focus on v1 scope**: Resist feature creep until core value is proven

Good luck! This is going to be a powerful tool.