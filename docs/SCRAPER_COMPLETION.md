# How We Know When All Snowflake Stories Are Scraped

## Automatic Completion Detection

The scraper automatically detects when all customer stories have been scraped using multiple heuristics:

### 1. **Duplicate URL Detection** (Primary Method)
- **How it works**: Before processing each page, we track how many unique URLs we've seen. After extracting links from a page, we check if any are new.
- **Completion signal**: If a page returns URLs but **all of them are duplicates** (already seen), we've likely reached the end and the pagination looped back to the beginning.
- **Example output**:
  ```
  ✓ Found 12 case study URLs on this page (0 new, 12 duplicates)
  ⚠ All URLs on this page were already seen - likely reached end and looped back
  Stopping pagination (found 245 total unique URLs)
  ```

### 2. **Empty Page Detection** (Secondary Method)
- **How it works**: If a page returns 0 case study links, we increment a counter. After 2 consecutive empty pages, we stop.
- **Completion signal**: Empty pages typically mean we've gone past the last page of results.
- **Example output**:
  ```
  No case studies found on this page (1/2 consecutive empty)
  No case studies found on this page (2/2 consecutive empty)
  Reached 2 consecutive empty pages, stopping pagination
  ```

### 3. **Failed Page Detection** (Fallback)
- **How it works**: If a page fails to load (network error, parsing error), we treat it like an empty page.
- **Completion signal**: After 2 consecutive failed pages, we assume we've gone too far.

### 4. **Safety Limits**
- **Max pages**: Can optionally set `max_pages=N` to limit scraping (useful for testing)
- **Hard limit**: Absolute maximum of 100 pages (should never be reached)

## Usage

### Full Scrape (Auto-Detect)
```python
scraper = SnowflakeScraper()
urls = scraper.get_customer_reference_urls()  # No max_pages = auto-detect
# Will scrape until completion is detected
```

### Limited Scrape (For Testing)
```python
scraper = SnowflakeScraper()
urls = scraper.get_customer_reference_urls(max_pages=5)  # Only scrape 5 pages
```

## Verification

After scraping completes, you'll see output like:
```
✓ Found 245 total unique case study URLs across 21 pages
```

To verify you got everything:

1. **Check the final count**: The scraper reports total unique URLs found
2. **Compare with Snowflake's website**: Manually check `/en/customers/all-customers/` to see if the count matches
3. **Check for gaps**: Look for any obvious customers missing from your dataset
4. **Query Neo4j**: 
   ```cypher
   MATCH (v:Vendor {name: "Snowflake"})-[:PUBLISHED]->(r:Reference)
   RETURN count(r) as total_references
   ```

## Edge Cases Handled

- **Pagination loops**: Detected via duplicate URLs
- **Sparse pages**: Some pages might have fewer than 12 results
- **Network failures**: Retries and graceful degradation
- **Rate limiting**: Built-in delays between requests

## When to Re-Run

You should re-run the scraper if:
- Snowflake adds new customer stories (check periodically)
- You notice missing customers in your dataset
- The website structure changes (pagination URLs might change)

The scraper is idempotent - re-running won't create duplicates (URLs are deduplicated in Neo4j).

