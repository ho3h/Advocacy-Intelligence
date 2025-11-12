# Scraping Phases/Stages

The scraping workflow consists of **4 distinct phases**, each with a specific purpose and output. This separation allows for flexibility, error recovery, and incremental processing.

## Phase 1: URL Discovery

**Purpose**: Find all customer reference URLs from vendor websites

**Process**:
1. **Pagination**: Iterate through paginated listing pages (e.g., `/en/customers/all-customers/?page=0&pageSize=12&offset=0`)
2. **Link Extraction**: Use regex to extract case study/video URLs from HTML content
3. **Completion Detection**: Automatically detect when all pages are scraped:
   - Stop when duplicate URLs appear (looped back)
   - Stop after N consecutive empty pages
   - Stop if max_pages limit reached
4. **URL Filtering**: Filter out invalid URLs (must have company name, exclude listing pages)

**Output**: List of unique reference URLs (e.g., `["https://snowflake.com/case-study/company1", ...]`)

**Code**: `scraper.get_customer_reference_urls(max_pages=None)`

**Example**:
```python
scraper = SnowflakeScraper()
urls = scraper.get_customer_reference_urls()  # Returns list of URLs
# Output: Found 245 total unique case study URLs across 21 pages
```

---

## Phase 2: Content Scraping

**Purpose**: Scrape the actual content from each reference URL

**Process**:
1. **Page Fetching**: Use HyperBrowser.ai to fetch each reference page
   - Handles JavaScript rendering
   - Bypasses Cloudflare/anti-bot protection
   - Returns HTML or markdown content
2. **Content Extraction**: Extract text content from the page
   - Prefer markdown format (cleaner)
   - Fallback to HTML if markdown unavailable
   - Extract customer name from title/URL
3. **Quality Filtering**: Filter out low-quality scrapes
   - Minimum word count: 100 words
   - Skip if content too short (likely failed scrape)
4. **Rate Limiting**: Wait 2 seconds between requests (configurable)

**Output**: List of reference dictionaries with:
- `url`: Source URL
- `raw_text`: Full scraped text content
- `customer_name`: Extracted customer name
- `scraped_date`: ISO timestamp
- `word_count`: Number of words
- `method`: "hyperbrowser"

**Code**: `scraper.scrape_all()` or `scraper.scrape_reference(url)`

**Example**:
```python
references = scraper.scrape_all()  # Scrapes all URLs from Phase 1
# Output: ✓ Scraped 245 references
```

---

## Phase 3: File Storage (Optional)

**Purpose**: Save each reference as an individual JSON file for backup and version control

**Process**:
1. **File Organization**: Organize files by vendor folder
   - Path: `data/scraped/{vendor}/{customer-slug}-{timestamp}.json`
   - Example: `data/scraped/snowflake/red-sea-global-20240115-143022.json`
2. **Filename Generation**: Create slug from customer name or URL
   - Sanitize special characters
   - Add timestamp for uniqueness
3. **JSON Serialization**: Save complete reference data as JSON
   - Includes all fields from Phase 2
   - Self-contained (can be loaded independently)

**Output**: Individual JSON files in `data/scraped/{vendor}/` directory

**Code**: `save_reference_file(vendor_name, reference_data)`

**Configuration**: Set `SAVE_RAW_DATA=false` in environment to disable

**Example**:
```python
from utils.file_storage import save_reference_file

for ref in references:
    filepath = save_reference_file('Snowflake', ref)
    # Saves to: data/scraped/snowflake/customer-name-20240115-143022.json
```

---

## Phase 4: Database Loading

**Purpose**: Load raw reference data into Neo4j graph database

**Process**:
1. **URL Deduplication**: Check if URL already exists in database
   - Uses MERGE on `Reference.url` property
   - Skips if URL already exists (idempotent)
2. **Node Creation**: Create Reference node with raw data
   - `id`: UUID
   - `url`: Source URL (unique)
   - `raw_text`: Full scraped text
   - `word_count`: Number of words
   - `scraped_date`: Timestamp
   - `classified`: false (flag for Phase 5)
3. **Vendor Relationship**: Link Reference to Vendor node
   - `(Vendor)-[:PUBLISHED]->(Reference)`

**Output**: Reference nodes in Neo4j with `classified=false` flag

**Code**: `db.load_raw_reference(vendor_name, reference_data)`

**Example**:
```python
from graph.neo4j_client import Neo4jClient

db = Neo4jClient()
for ref in references:
    ref_id = db.load_raw_reference('Snowflake', ref)
    # Creates Reference node, links to Vendor node
```

---

## Complete Workflow

The full pipeline runs all phases sequentially:

```python
# Phase 1: URL Discovery
scraper = SnowflakeScraper()
urls = scraper.get_customer_reference_urls()

# Phase 2: Content Scraping
references = scraper.scrape_all()  # Uses URLs from Phase 1

# Phase 3: File Storage (optional)
for ref in references:
    save_reference_file('Snowflake', ref)

# Phase 4: Database Loading
db = Neo4jClient()
for ref in references:
    db.load_raw_reference('Snowflake', ref)
```

**Note**: Phase 5 (Classification) is separate and runs after scraping:
- Queries database for `classified=false` references
- Uses Gemini to extract structured data
- Updates Reference nodes with classification results

---

## Phase Characteristics

| Phase | Input | Output | Idempotent | Can Skip |
|-------|-------|--------|------------|----------|
| **1. URL Discovery** | Vendor base URL | List of URLs | ✅ Yes | ❌ No |
| **2. Content Scraping** | List of URLs | Reference dicts | ✅ Yes* | ✅ Yes |
| **3. File Storage** | Reference dicts | JSON files | ✅ Yes | ✅ Yes |
| **4. Database Loading** | Reference dicts | Neo4j nodes | ✅ Yes | ✅ Yes |

*Content scraping is idempotent if you check for existing URLs before scraping

---

## Error Handling

Each phase handles errors independently:

- **Phase 1**: If pagination fails, returns partial URL list
- **Phase 2**: If a page fails to scrape, skips it and continues
- **Phase 3**: If file save fails, logs error but continues
- **Phase 4**: If database load fails, skips duplicate URLs automatically

This allows the pipeline to continue even if individual steps fail.

---

## Resuming/Re-running

Because phases are separated:

- **Re-run Phase 1**: Discovers URLs again (useful if vendor adds new references)
- **Re-run Phase 2**: Can scrape specific URLs without re-discovering
- **Re-run Phase 3**: Can save files from existing database data
- **Re-run Phase 4**: Safe to re-run (deduplication prevents duplicates)

This flexibility makes it easy to:
- Add new references incrementally
- Re-scrape failed pages
- Re-process data after code improvements
- Export data to different formats

