"""Phase 2: Scrape content from discovered MongoDB URLs (loads URLs from file, skips Phase 1)."""

import sys
import os
import json
import glob
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scrapers.mongodb_scraper import MongoDBScraper
from utils.file_storage import save_reference_file


def get_latest_discovered_urls():
    """Get the most recent discovered URLs file with the most URLs."""
    url_files = glob.glob('data/scraped/mongodb/discovered_urls*.json')
    if not url_files:
        raise FileNotFoundError("No discovered URLs file found. Run Phase 1 first.")
    
    # Find file with most URLs
    best_file = None
    max_urls = 0
    for fpath in url_files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                url_count = len(data.get('urls', []))
                if url_count > max_urls:
                    max_urls = url_count
                    best_file = fpath
        except:
            continue
    
    if not best_file:
        # Fallback to most recent by modification time
        url_files.sort(key=os.path.getmtime, reverse=True)
        best_file = url_files[0]
    
    return best_file


def main():
    """Run Phase 2: Content Scraping using discovered URLs."""
    
    print("=" * 70)
    print("PHASE 2: CONTENT SCRAPING (MONGODB)")
    print("=" * 70)
    
    # Load URLs from file
    try:
        urls_file = get_latest_discovered_urls()
        print(f"\n📂 Loading URLs from: {os.path.basename(urls_file)}")
        
        with open(urls_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            urls = data.get('urls', [])
            total_in_file = data.get('total_urls', len(urls))
        
        print(f"✓ Loaded {len(urls)} URLs from file\n")
    except FileNotFoundError as e:
        print(f"✗ {e}")
        return
    
    if not urls:
        print("✗ No URLs found in file")
        return
    
    # Filter out listing pages and non-English duplicates (keep English versions)
    filtered_urls = []
    seen_customers = set()
    
    for url in urls:
        # Skip listing pages
        if url.rstrip('/').endswith(('/customers', '/customer-case-studies', '/solutions/customer-case-studies')):
            continue
        
        # Extract customer name from URL for deduplication
        url_lower = url.lower()
        customer_key = None
        
        if '/customers/' in url_lower:
            parts = url.split('/')
            if 'customers' in parts:
                idx = parts.index('customers')
                if idx + 1 < len(parts):
                    customer_key = parts[idx + 1]
        elif '/customer-case-studies/' in url_lower:
            parts = url.split('/')
            if 'customer-case-studies' in parts:
                idx = parts.index('customer-case-studies')
                if idx + 1 < len(parts):
                    customer_key = parts[idx + 1]
        
        # Prefer English URLs (no language prefix)
        if customer_key:
            if customer_key not in seen_customers:
                filtered_urls.append(url)
                seen_customers.add(customer_key)
            elif not any(lang in url for lang in ['/fr-fr/', '/zh-cn/', '/zh-tw/', '/ko-kr/', '/ja-jp/']):
                # Replace non-English with English version if we find one
                for i, existing_url in enumerate(filtered_urls):
                    existing_parts = existing_url.split('/')
                    if customer_key in existing_parts:
                        if any(lang in existing_url for lang in ['/fr-fr/', '/zh-cn/', '/zh-tw/', '/ko-kr/', '/ja-jp/']):
                            filtered_urls[i] = url
                            break
    
    urls = filtered_urls
    print(f"📋 Filtered to {len(urls)} unique customer story URLs (removed duplicates and listing pages)\n")
    
    if not urls:
        print("✗ No customer story URLs found")
        return
    
    # Initialize scraper (this will close any active sessions)
    scraper = MongoDBScraper(delay=2)
    
    # Scrape all URLs
    print("=" * 70)
    print("SCRAPING CONTENT")
    print("=" * 70)
    print(f"\n📋 Scraping {len(urls)} customer story URLs")
    print(f"⏱️  Estimated time: {len(urls) * (scraper.delay + 15) / 60:.1f} - {len(urls) * (scraper.delay + 30) / 60:.1f} minutes")
    print(f"💰 Estimated cost: ${len(urls) * 0.02:.2f} - ${len(urls) * 0.05:.2f}\n")
    
    # Check for already-scraped URLs (resume capability)
    existing_files = glob.glob('data/scraped/mongodb/*.json')
    existing_files = [f for f in existing_files if 'discovered_urls' not in f]
    scraped_urls = set()
    for filepath in existing_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'url' in data:
                    scraped_urls.add(data['url'])
        except:
            pass
    
    if scraped_urls:
        print(f"📋 Found {len(scraped_urls)} already-scraped URLs (will skip)")
        urls = [url for url in urls if url not in scraped_urls]
        print(f"📋 Remaining to scrape: {len(urls)} URLs\n")
    
    references = []
    skipped_low_quality = 0
    skipped_already_done = len(scraped_urls)
    failed = 0
    failed_errors = []  # Track error messages
    start_time = time.time()
    
    # Use tqdm if available
    try:
        from tqdm import tqdm
        url_iterator = tqdm(enumerate(urls, 1), total=len(urls), desc="Scraping", unit="ref")
        USE_TQDM = True
    except ImportError:
        url_iterator = enumerate(urls, 1)
        USE_TQDM = False
    
    for i, url in url_iterator:
        # Show progress
        if not USE_TQDM:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (len(urls) - i) / rate if rate > 0 else 0
            print(f"\n[{i}/{len(urls)}] ({i/len(urls)*100:.1f}%) | "
                  f"Elapsed: {elapsed/60:.1f}m | "
                  f"ETA: {remaining/60:.1f}m | "
                  f"Success: {len(references)}", flush=True)
            print(f"  📄 Scraping: {url[:70]}...", flush=True)
        
        try:
            ref_data = scraper.scrape_reference(url)
            if ref_data:
                # Filter out low-quality scrapes (too short, likely failed)
                if ref_data['word_count'] < 100:
                    skipped_low_quality += 1
                    error_msg = f"Low quality ({ref_data['word_count']} words)"
                    failed_errors.append(f"{url[:60]}... - {error_msg}")
                    if not USE_TQDM:
                        print(f"  ⚠ Skipping low-quality scrape ({ref_data['word_count']} words)", flush=True)
                    continue
                
                references.append(ref_data)
                
                # Phase 3: Save to file immediately (so we don't lose progress if interrupted)
                filepath = save_reference_file('MongoDB', ref_data)
                if filepath:
                    if not USE_TQDM:
                        print(f"  💾 Saved to: {os.path.basename(filepath)}", flush=True)
                
                if not USE_TQDM:
                    print(f"  ✓ Successfully scraped: {ref_data['customer_name']} ({ref_data['word_count']} words)", flush=True)
            else:
                failed += 1
                error_msg = "scrape_reference returned None"
                failed_errors.append(f"{url[:60]}... - {error_msg}")
                if not USE_TQDM:
                    print(f"  ✗ Failed to scrape (returned None)", flush=True)
        except Exception as e:
            failed += 1
            error_msg = str(e)[:100]  # Truncate long errors
            failed_errors.append(f"{url[:60]}... - {error_msg}")
            if USE_TQDM:
                # tqdm doesn't show print statements well, so write to stderr
                import sys
                print(f"\n✗ [{i}/{len(urls)}] Failed: {url[:60]}... - {error_msg}", file=sys.stderr, flush=True)
            else:
                print(f"  ✗ Failed with error: {error_msg}", flush=True)
        
        # Be respectful - wait between requests
        if i < len(urls):
            time.sleep(scraper.delay)
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("SCRAPING SUMMARY")
    print("=" * 70)
    print(f"✓ Successfully scraped: {len(references)} references")
    print(f"💾 Files saved: {len(references)} files in data/scraped/mongodb/")
    print(f"⏭️  Skipped (already done): {skipped_already_done}")
    print(f"⚠ Skipped (low quality): {skipped_low_quality}")
    print(f"✗ Failed: {failed}")
    print(f"⏱️  Total time: {elapsed_time/60:.1f} minutes ({elapsed_time:.0f} seconds)")
    if len(references) > 0:
        print(f"📊 Average time per reference: {elapsed_time/len(references):.1f} seconds")
    
    if failed_errors:
        print(f"\n❌ FAILURE DETAILS (showing first 10):")
        for error in failed_errors[:10]:
            print(f"   {error}")
        if len(failed_errors) > 10:
            print(f"   ... and {len(failed_errors) - 10} more failures")
    
    print("=" * 70 + "\n")
    
    print(f"✓ Phase 2 & 3 complete! Scraped and saved {len(references)} customer story references")
    print(f"  Files saved in: data/scraped/mongodb/")
    print(f"  References are ready for Phase 4 (database loading)")


if __name__ == '__main__':
    main()

