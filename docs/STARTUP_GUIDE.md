# Startup Guide: Adding a New Vendor

**Goal**: Add a new vendor to the system in 3 simple steps.

## Quick Start

```bash
# 1. Add vendor config to data/vendors.json
# 2. Run the pipeline
python scripts/run_pipeline.py --vendors newvendor

# That's it! The pipeline handles everything:
# - Phase 1: URL Discovery (sitemap or pagination)
# - Phase 2: Content Scraping (Scrapy first, HyperBrowser fallback)
# - Phase 3: Database Loading (with deduplication)
# - Phase 4: Classification (only unclassified references)
```

## Step-by-Step Process

### Step 1: Check if Vendor Already Exists

```bash
grep -i "vendor_name" data/vendors.json
```

**If vendor exists**: Just run `python scripts/run_pipeline.py --vendors vendor_key`

**If vendor doesn't exist**: Continue to Step 2

### Step 2: Add Vendor Configuration

Edit `data/vendors.json` and add your vendor:

#### For Sitemap-Based Discovery (Preferred - Fast & Free!)

```json
{
  "newvendor": {
    "name": "New Vendor",
    "website": "https://newvendor.com",
    "discovery_method": "sitemap",
    "scraper_class": "UniversalScraper",
    "enabled": true,
    "error_handling": {
      "retry_on_failure": true,
      "max_retries": 3,
      "skip_on_error": false
    },
    "scraper": {
      "link_patterns": ["/customers/", "/case-studies/"],
      "exclude_patterns": ["/customers/", "?filter="]
    }
  }
}
```

**Also add to `src/utils/sitemap_discovery.py` → `VENDOR_CONFIGS`:**

```python
VENDOR_CONFIGS = {
    # ... existing configs ...
    'newvendor': {
        'base_url': 'https://newvendor.com',
        'sitemap_path': '/sitemap.xml',
        'url_patterns': [r'/customers/', r'/case-studies/'],
        'exclude_patterns': [r'/customers/?$', r'\?', r'#'],
    },
}
```

#### For Pagination-Based Discovery (Fallback)

```json
{
  "newvendor": {
    "name": "New Vendor",
    "website": "https://newvendor.com",
    "discovery_method": "pagination",
    "scraper_class": "UniversalScraper",
    "enabled": true,
    "error_handling": {
      "retry_on_failure": true,
      "max_retries": 3,
      "skip_on_error": false
    },
    "scraper": {
      "link_patterns": ["/customers/", "/case-study/"],
      "exclude_patterns": ["/all-customers/", "/video"],
      "pagination": {
        "path": "/customers/",
        "strategy": "page_number",
        "page_param": "page",
        "page_size": 12,
        "max_consecutive_empty": 2,
        "create_session": false
      }
    }
  }
}
```

**Pagination Strategy Options:**
- `"page_number"`: Simple page numbers (`?page=1`, `?page=2`)
- `"offset"`: Offset-based (`?page=0&pageSize=12&offset=0`)

### Step 3: Run the Pipeline

```bash
# Test configuration (dry run - no changes made)
python scripts/run_pipeline.py --vendors newvendor --phases 1 --dry-run

# Run Phase 1 only (URL discovery)
python scripts/run_pipeline.py --vendors newvendor --phases 1

# Run Phase 2 only (content scraping)
python scripts/run_pipeline.py --vendors newvendor --phases 2

# Run full pipeline (all 4 phases)
python scripts/run_pipeline.py --vendors newvendor

# Process multiple vendors
python scripts/run_pipeline.py --vendors vendor1,vendor2,vendor3
```

## What Happens Automatically

The pipeline handles everything:

1. **Phase 1: URL Discovery**
   - Sitemap: Parses XML, extracts customer URLs (~10 seconds, free)
   - Pagination: Iterates through pages, extracts links (minutes, uses Scrapy/HyperBrowser)
   - Saves URLs to `data/scraped/{vendor}/discovered_urls-{timestamp}.json`
   - **Idempotent**: Skips URLs already in database

2. **Phase 2: Content Scraping**
   - Uses **Scrapy first** (free, fast) for simple pages
   - Falls back to **HyperBrowser.ai** for JavaScript/Cloudflare protection
   - Saves each reference to `data/scraped/{vendor}/{customer-slug}-{timestamp}.json`
   - Filters low-quality scrapes (<100 words)
   - **Idempotent**: Skips URLs already scraped

3. **Phase 3: Database Loading**
   - Loads scraped references into Neo4j
   - Creates Reference nodes with raw text
   - Links to Vendor nodes
   - Sets `classified=false` flag
   - **Idempotent**: Uses MERGE, no duplicates

4. **Phase 4: Classification**
   - Uses Google Gemini to extract structured data
   - Creates Customer, Industry, UseCase, Outcome, Persona, Technology nodes
   - Sets `classified=true` when complete
   - **Idempotent**: Only processes `classified=false` references

## Verifying Results

```bash
# Check scraped files
ls data/scraped/newvendor/

# Check pipeline report
cat logs/pipeline_report_*.json | jq

# Query Neo4j Browser (from AuraDB console)
MATCH (v:Vendor {name: "New Vendor"})-[:PUBLISHED]->(r:Reference)
RETURN count(r) as reference_count
```

## Common Issues

### No URLs Found

**Check:**
- Sitemap exists? `curl -I https://vendor.com/sitemap.xml`
- Link patterns match actual URLs? Inspect sitemap or pagination pages
- Exclude patterns too aggressive? Remove some patterns

### Content Too Short

**Check:**
- Scrapy detected anti-bot protection? Check logs
- HyperBrowser.ai API key set? (needed for JavaScript-heavy sites)
- Page structure changed? Inspect manually

### Classification Fails

**Check:**
- Google API key valid?
- API quota available?
- Reference has enough content? (>100 words)

## Daily Workflow

For daily updates (cost-effective!):

```bash
# Run all enabled vendors
python scripts/run_pipeline.py

# Only processes new URLs/content (idempotent)
# Estimated cost: $0-5 per day (only new content)
```

## Adding Multiple Vendors

Just add all vendor configs to `data/vendors.json`, then:

```bash
# Process all at once
python scripts/run_pipeline.py --vendors vendor1,vendor2,vendor3

# Or process all enabled vendors
python scripts/run_pipeline.py
```

## Summary

**The workflow is simple:**
1. ✅ Add vendor config to `data/vendors.json` (and `sitemap_discovery.py` if using sitemap)
2. ✅ Run `python scripts/run_pipeline.py --vendors vendor_key`
3. ✅ Done! Pipeline handles everything automatically

**No Python code needed!** Just JSON configuration.

