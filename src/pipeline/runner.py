"""Main pipeline runner that orchestrates all 4 phases for vendors."""

import os
import json
import time
import glob
from datetime import datetime
from typing import List, Dict, Optional, Set
from pathlib import Path

from graph.neo4j_client import Neo4jClient
from classifiers.gemini_classifier import ReferenceClassifier
try:
    from utils.sitemap_discovery import discover_vendor_urls
except ImportError:
    # Fallback if sitemap_discovery not available
    def discover_vendor_urls(vendor_key):
        raise NotImplementedError("Sitemap discovery not available")
from utils.file_storage import save_reference_file

from .vendor_config import get_vendor_config, get_enabled_vendors
from .scraper_registry import get_scraper
from .idempotency import (
    get_existing_urls,
    filter_new_urls,
    get_scraped_urls,
    filter_unscraped_urls,
    get_unclassified_references
)
from .reporting import PipelineReporter

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class PipelineRunner:
    """Orchestrates the 4-phase pipeline for processing vendors."""
    
    def __init__(self, db: Optional[Neo4jClient] = None, classifier: Optional[ReferenceClassifier] = None):
        """
        Initialize pipeline runner.
        
        Args:
            db: Neo4jClient instance (creates new if None)
            classifier: ReferenceClassifier instance (creates new if None)
        """
        self.db = db or Neo4jClient()
        self.classifier = classifier or ReferenceClassifier()
        self.reporter = PipelineReporter()
        
        # Verify database connection
        if not self.db.verify_connection():
            raise ConnectionError("Failed to connect to Neo4j database")
        
        # Create indexes
        self.db.create_indexes()
    
    def run_phase1_discovery(
        self,
        vendor_key: str,
        force: bool = False,
        dry_run: bool = False
    ) -> Dict:
        """
        Phase 1: URL Discovery
        
        Discovers customer reference URLs using sitemap or pagination.
        Checks Neo4j for existing URLs to avoid re-discovery.
        
        Args:
            vendor_key: Vendor key (e.g., 'mongodb')
            force: Skip idempotency checks
            dry_run: Show what would be done without executing
            
        Returns:
            Dict with results: {'discovered': int, 'new': int, 'skipped': int, 'urls': List[str]}
        """
        vendor_config = get_vendor_config(vendor_key)
        if not vendor_config:
            raise ValueError(f"Vendor '{vendor_key}' not found in configuration")
        
        vendor_name = vendor_config['name']
        discovery_method = vendor_config['discovery_method']
        
        self.reporter.log(f"Phase 1: URL Discovery for {vendor_name}")
        
        # Discover URLs
        if discovery_method == 'sitemap':
            try:
                # discover_vendor_urls expects vendor key (lowercase)
                discovered_urls = discover_vendor_urls(vendor_key.lower())
            except Exception as e:
                self.reporter.log_error(f"Failed to discover URLs via sitemap: {e}")
                return {'discovered': 0, 'new': 0, 'skipped': 0, 'urls': [], 'error': str(e)}
        elif discovery_method == 'pagination':
            try:
                scraper = get_scraper(vendor_key)
                discovered_urls = scraper.get_customer_reference_urls()
            except Exception as e:
                self.reporter.log_error(f"Failed to discover URLs via pagination: {e}")
                return {'discovered': 0, 'new': 0, 'skipped': 0, 'urls': [], 'error': str(e)}
        else:
            raise ValueError(f"Unknown discovery method: {discovery_method}")
        
        discovered_count = len(discovered_urls)
        
        # Idempotency check: filter out URLs already in Neo4j
        if not force:
            new_urls = filter_new_urls(vendor_name, discovered_urls, self.db)
            skipped_count = discovered_count - len(new_urls)
        else:
            new_urls = discovered_urls
            skipped_count = 0
        
        if dry_run:
            self.reporter.log(f"  [DRY RUN] Would discover {discovered_count} URLs, {len(new_urls)} new")
            return {'discovered': discovered_count, 'new': len(new_urls), 'skipped': skipped_count, 'urls': new_urls}
        
        # Save discovered URLs to file
        if new_urls:
            vendor_dir = Path('data') / 'scraped' / vendor_key.lower()
            vendor_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            output_file = vendor_dir / f'discovered_urls-{timestamp}.json'
            
            data = {
                'vendor': vendor_key,
                'discovery_method': discovery_method,
                'discovery_date': datetime.now().isoformat(),
                'total_urls': len(new_urls),
                'urls': new_urls
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.reporter.log(f"  ✓ Saved {len(new_urls)} URLs to {output_file.name}")
        
        return {
            'discovered': discovered_count,
            'new': len(new_urls),
            'skipped': skipped_count,
            'urls': new_urls
        }
    
    def run_phase2_scraping(
        self,
        vendor_key: str,
        force: bool = False,
        dry_run: bool = False
    ) -> Dict:
        """
        Phase 2: Content Scraping
        
        Scrapes content from URLs discovered in Phase 1.
        Checks filesystem for existing scraped files to avoid re-scraping.
        
        Args:
            vendor_key: Vendor key
            force: Skip idempotency checks
            dry_run: Show what would be done without executing
            
        Returns:
            Dict with results: {'scraped': int, 'skipped': int, 'failed': int}
        """
        vendor_config = get_vendor_config(vendor_key)
        if not vendor_config:
            raise ValueError(f"Vendor '{vendor_key}' not found")
        
        vendor_name = vendor_config['name']
        
        self.reporter.log(f"Phase 2: Content Scraping for {vendor_name}")
        
        # Load URLs from latest discovered_urls file
        vendor_dir = Path('data') / 'scraped' / vendor_key.lower()
        url_files = glob.glob(str(vendor_dir / 'discovered_urls*.json'))
        
        if not url_files:
            self.reporter.log(f"  ⚠ No discovered URLs file found. Run Phase 1 first.")
            return {'scraped': 0, 'skipped': 0, 'failed': 0, 'error': 'No URLs file'}
        
        # Get file with most URLs
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
            except Exception:
                continue
        
        if not best_file:
            url_files.sort(key=os.path.getmtime, reverse=True)
            best_file = url_files[0]
        
        # Load URLs
        with open(best_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            urls = data.get('urls', [])
        
        # Idempotency check: filter out URLs already scraped
        if not force:
            urls = filter_unscraped_urls(vendor_key, urls)
            skipped_count = len(data.get('urls', [])) - len(urls)
        else:
            skipped_count = 0
        
        if not urls:
            self.reporter.log(f"  ✓ All URLs already scraped (skipped {skipped_count})")
            return {'scraped': 0, 'skipped': skipped_count, 'failed': 0}
        
        if dry_run:
            self.reporter.log(f"  [DRY RUN] Would scrape {len(urls)} URLs")
            return {'scraped': 0, 'skipped': skipped_count, 'failed': 0}
        
        # Get scraper
        scraper = get_scraper(vendor_key)
        
        # Scrape URLs
        scraped_count = 0
        failed_count = 0
        
        iterator = tqdm(urls, desc=f"Scraping {vendor_name}") if TQDM_AVAILABLE else urls
        
        for url in iterator:
            try:
                ref_data = scraper.scrape_reference(url)
                if ref_data and ref_data.get('word_count', 0) >= 100:
                    ref_data['vendor_website'] = vendor_config['website']
                    filepath = save_reference_file(vendor_name, ref_data)
                    if filepath:
                        scraped_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                self.reporter.log_error(f"Failed to scrape {url[:60]}...: {e}")
                failed_count += 1
            
            # Rate limiting
            if scraper.delay:
                time.sleep(scraper.delay)
        
        self.reporter.log(f"  ✓ Scraped {scraped_count} references, failed {failed_count}")
        
        return {
            'scraped': scraped_count,
            'skipped': skipped_count,
            'failed': failed_count
        }
    
    def run_phase3_loading(
        self,
        vendor_key: str,
        force: bool = False,
        dry_run: bool = False
    ) -> Dict:
        """
        Phase 3: Database Loading
        
        Loads scraped references from files into Neo4j.
        Already idempotent (load_raw_reference checks for duplicates).
        
        Args:
            vendor_key: Vendor key
            force: Skip idempotency checks (not applicable, always idempotent)
            dry_run: Show what would be done without executing
            
        Returns:
            Dict with results: {'loaded': int, 'skipped': int}
        """
        vendor_config = get_vendor_config(vendor_key)
        if not vendor_config:
            raise ValueError(f"Vendor '{vendor_key}' not found")
        
        vendor_name = vendor_config['name']
        
        self.reporter.log(f"Phase 3: Database Loading for {vendor_name}")
        
        # Load reference files
        vendor_dir = Path('data') / 'scraped' / vendor_key.lower()
        ref_files = glob.glob(str(vendor_dir / '*.json'))
        ref_files = [f for f in ref_files if 'discovered_urls' not in f]
        
        if not ref_files:
            self.reporter.log(f"  ⚠ No reference files found")
            return {'loaded': 0, 'skipped': 0}
        
        if dry_run:
            self.reporter.log(f"  [DRY RUN] Would load {len(ref_files)} reference files")
            return {'loaded': 0, 'skipped': 0}
        
        # Load to Neo4j
        loaded_count = 0
        skipped_count = 0
        
        iterator = tqdm(ref_files, desc=f"Loading {vendor_name}") if TQDM_AVAILABLE else ref_files
        
        for filepath in iterator:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    ref_data = json.load(f)
                
                ref_data['vendor_website'] = vendor_config['website']
                ref_id = self.db.load_raw_reference(vendor_name, ref_data)
                
                if ref_id:
                    loaded_count += 1
                else:
                    skipped_count += 1  # Already exists
            except Exception as e:
                self.reporter.log_error(f"Failed to load {os.path.basename(filepath)}: {e}")
        
        self.reporter.log(f"  ✓ Loaded {loaded_count} references, skipped {skipped_count} duplicates")
        
        return {
            'loaded': loaded_count,
            'skipped': skipped_count
        }
    
    def run_phase4_classification(
        self,
        vendor_key: str,
        force: bool = False,
        dry_run: bool = False
    ) -> Dict:
        """
        Phase 4: Classification
        
        Classifies unclassified references using Gemini.
        Only processes references with classified=false.
        
        Args:
            vendor_key: Vendor key
            force: Re-classify all references (set classified=false first)
            dry_run: Show what would be done without executing
            
        Returns:
            Dict with results: {'classified': int, 'failed': int}
        """
        vendor_config = get_vendor_config(vendor_key)
        if not vendor_config:
            raise ValueError(f"Vendor '{vendor_key}' not found")
        
        vendor_name = vendor_config['name']
        
        self.reporter.log(f"Phase 4: Classification for {vendor_name}")
        
        # Get unclassified references
        if force:
            # Get all references for vendor
            with self.db.driver.session() as session:
                result = session.run("""
                    MATCH (v:Vendor {name: $vendor_name})-[:PUBLISHED]->(r:Reference)
                    RETURN r.id as id, r.url as url, r.raw_text as text
                    LIMIT 1000
                """, {'vendor_name': vendor_name})
                unclassified = [dict(record) for record in result]
        else:
            unclassified = get_unclassified_references(vendor_name, self.db, limit=1000)
        
        if not unclassified:
            self.reporter.log(f"  ✓ No unclassified references")
            return {'classified': 0, 'failed': 0}
        
        if dry_run:
            self.reporter.log(f"  [DRY RUN] Would classify {len(unclassified)} references")
            return {'classified': 0, 'failed': 0}
        
        # Classify references
        classified_count = 0
        failed_count = 0
        
        iterator = tqdm(unclassified, desc=f"Classifying {vendor_name}") if TQDM_AVAILABLE else unclassified
        
        for ref in iterator:
            try:
                classification = self.classifier.classify(ref['text'], ref['url'])
                if classification:
                    self.db.update_classification(ref['id'], classification)
                    classified_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                self.reporter.log_error(f"Failed to classify {ref['url'][:60]}...: {e}")
                failed_count += 1
        
        self.reporter.log(f"  ✓ Classified {classified_count} references, failed {failed_count}")
        
        return {
            'classified': classified_count,
            'failed': failed_count
        }
    
    def run_all_phases(
        self,
        vendor_key: str,
        phases: Optional[List[int]] = None,
        skip_phases: Optional[List[int]] = None,
        force: bool = False,
        dry_run: bool = False
    ) -> Dict:
        """
        Run all phases for a vendor.
        
        Args:
            vendor_key: Vendor key
            phases: List of phase numbers to run (1-4). None = all phases
            skip_phases: List of phase numbers to skip
            force: Skip idempotency checks
            dry_run: Show what would be done without executing
            
        Returns:
            Dict with results from all phases
        """
        if phases is None:
            phases = [1, 2, 3, 4]
        
        if skip_phases:
            phases = [p for p in phases if p not in skip_phases]
        
        results = {}
        
        phase_methods = {
            1: self.run_phase1_discovery,
            2: self.run_phase2_scraping,
            3: self.run_phase3_loading,
            4: self.run_phase4_classification,
        }
        
        for phase_num in phases:
            if phase_num not in phase_methods:
                continue
            
            try:
                phase_result = phase_methods[phase_num](
                    vendor_key,
                    force=force,
                    dry_run=dry_run
                )
                results[f'phase{phase_num}'] = phase_result
            except Exception as e:
                error_msg = f"Phase {phase_num} failed: {e}"
                self.reporter.log_error(error_msg)
                results[f'phase{phase_num}'] = {'error': str(e)}
                
                # Check if we should skip on error
                vendor_config = get_vendor_config(vendor_key)
                if vendor_config and vendor_config.get('error_handling', {}).get('skip_on_error', False):
                    break
        
        return results
    
    def run_all_vendors(
        self,
        vendor_keys: Optional[List[str]] = None,
        phases: Optional[List[int]] = None,
        skip_phases: Optional[List[int]] = None,
        force: bool = False,
        dry_run: bool = False
    ) -> Dict:
        """
        Run pipeline for multiple vendors.
        
        Args:
            vendor_keys: List of vendor keys to process. None = all enabled vendors
            phases: List of phase numbers to run (1-4). None = all phases
            skip_phases: List of phase numbers to skip
            force: Skip idempotency checks
            dry_run: Show what would be done without executing
            
        Returns:
            Dict mapping vendor keys to their results
        """
        if vendor_keys is None:
            vendor_keys = get_enabled_vendors()
        
        all_results = {}
        
        for vendor_key in vendor_keys:
            vendor_config = get_vendor_config(vendor_key)
            if not vendor_config:
                self.reporter.log_error(f"Vendor '{vendor_key}' not found, skipping")
                continue
            
            if not vendor_config.get('enabled', True):
                self.reporter.log(f"Skipping disabled vendor: {vendor_key}")
                continue
            
            vendor_name = vendor_config['name']
            self.reporter.log(f"\n{'='*70}")
            self.reporter.log(f"Processing: {vendor_name} ({vendor_key})")
            self.reporter.log(f"{'='*70}")
            
            try:
                results = self.run_all_phases(
                    vendor_key,
                    phases=phases,
                    skip_phases=skip_phases,
                    force=force,
                    dry_run=dry_run
                )
                all_results[vendor_key] = results
            except Exception as e:
                error_msg = f"Failed to process {vendor_name}: {e}"
                self.reporter.log_error(error_msg)
                all_results[vendor_key] = {'error': str(e)}
                
                # Check if we should skip on error
                if vendor_config.get('error_handling', {}).get('skip_on_error', False):
                    continue
        
        return all_results

