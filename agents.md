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
- **BeautifulSoup4** for primary web scraping (free, fast)
- **HyperBrowser.ai** for fallback scraping (when blocked by Cloudflare/anti-bot protection)
- **Streamlit** for UI (later phase)
- **python-dotenv** for environment management

### Critical Design Patterns

#### 1. Separation of ConcernsScraping → Load Raw to DB → Classify → Enrich Graph
Each step is a separate function/module. Raw content is always preserved.

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

### Core Nodes
```cypher// Vendor who published the reference
(:Vendor {
name: string,           // "Snowflake"
website: string,        // "https://snowflake.com"
scraped_date: datetime
})// Customer being referenced
(:Customer {
name: string,           // "Capital One"
size: string,           // "Enterprise"
region: string,         // "North America"
country: string         // "United States" (optional)
})// The reference content itself
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
})// Industry categories
(:Industry {name: string})  // "Financial Services"// Use cases solved
(:UseCase {
name: string,           // "Real-time Analytics"
description: string     // (optional)
})// Job titles/personas featured
(:Persona {
title: string,          // "Chief Data Officer"
seniority: string       // "C-Level", "VP", "Director"
})// Business outcomes achieved
(:Outcome {
type: string,           // "performance", "cost_savings", "revenue_impact"
description: string,    // "10x faster queries"
metric: string          // (optional) "10x"
})// Technologies mentioned
(:Technology {
name: string,           // "AWS", "dbt"
category: string        // "Cloud Platform", "Transformation Tool"
})

### Core Relationships
```cypher(Vendor)-[:PUBLISHED]->(Reference)
(Reference)-[:FEATURES]->(Customer)
(Customer)-[:IN_INDUSTRY]->(Industry)
(Reference)-[:ADDRESSES_USE_CASE]->(UseCase)
(Reference)-[:ACHIEVED_OUTCOME]->(Outcome)
(Reference)-[:MENTIONS_PERSONA]->(Persona)
(Customer)-[:USES_TECH]->(Technology)

## Common Tasks & How to Approach Them

### Task: Add a New Scraper

1. Create new file in `src/scrapers/{vendor}_scraper.py`
2. Follow the pattern from `snowflake_scraper.py` (hybrid BeautifulSoup + HyperBrowser.ai approach)
3. Implement these methods:
   - `get_customer_reference_urls()` or `get_reference_urls()` - Returns list of URLs to scrape
   - `scrape_reference(url)` - Returns dict with raw_text, customer_name, metadata
   - `scrape_all()` - Orchestrates full scraping workflow
4. Handle pagination if needed (see Snowflake scraper for pagination pattern)
5. Add rate limiting (2-3 second delays between requests)
6. Use HyperBrowser.ai fallback when BeautifulSoup fails or content is suspiciously short
7. Return consistent schema:
```python{
'url': str,
'raw_text': str,
'raw_html': str,  # optional
'customer_name': str,  # if obvious from URL/title
'scraped_date': str,  # ISO format
'word_count': int
}

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
- HyperBrowser.ai: ~$0.01-0.05 per page (only used when BeautifulSoup fails)
- Total cost: ~$1-5 for v1 dataset (mostly HyperBrowser.ai costs)

Track usage during development.

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

**Phase 1: Proof of Concept** (In Progress)

Tasks:
1. ✅ Set up project structure
2. ✅ Build Snowflake scraper (with pagination and HyperBrowser.ai fallback)
3. ✅ Load raw data to AuraDB
4. ✅ Create Gemini classification function
5. ⏳ Validate data quality (manual QA on 20+ classifications)
6. ⏳ Run full pipeline with 20+ references

Next: Once Snowflake is working end-to-end, replicate for Databricks.

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