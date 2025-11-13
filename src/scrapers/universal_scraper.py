"""Universal scraper that works for all vendors using configuration.

This scraper replaces vendor-specific scrapers by accepting vendor configuration
and adapting its behavior accordingly. This eliminates code duplication and makes
adding new vendors as simple as updating vendors.json.
"""

import time
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from typing import Optional, Dict, Any, List, Set

import requests
from dotenv import load_dotenv

# Try to import tqdm for progress bars (optional)
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Import Scrapy scraper utility
try:
    from utils.scrapy_scraper import ScrapyScraper, SCRAPY_AVAILABLE
except ImportError:
    SCRAPY_AVAILABLE = False

# Import pagination utilities
from scrapers.pagination import (
    PaginationConfig,
    OffsetPaginationStrategy,
    PageNumberPaginationStrategy,
    paginate_with_strategy
)

load_dotenv()

# Try to import HyperBrowser.ai (fallback dependency)
try:
    from hyperbrowser import Hyperbrowser
    from hyperbrowser.models import StartScrapeJobParams, ScrapeOptions
    from hyperbrowser.models.session import CreateSessionParams as SessionCreateParams
    HYPERBROWSER_AVAILABLE = True
except ImportError:
    HYPERBROWSER_AVAILABLE = False


class UniversalScraper:
    """Universal scraper that adapts to vendor configuration.
    
    Uses Scrapy first (cost-effective), then falls back to HyperBrowser.ai for JavaScript rendering.
    Configured via vendor config in data/vendors.json.
    """
    
    # Common anti-bot indicators
    BLOCK_INDICATORS = [
        'cloudflare',
        'checking your browser',
        'please wait',
        'access denied',
        'blocked',
        'captcha',
        'challenge',
        'ddos protection'
    ]
    
    def __init__(self, vendor_config: Dict[str, Any], delay: float = 2.0):
        """
        Initialize universal scraper with vendor configuration.
        
        Args:
            vendor_config: Vendor configuration dict from vendors.json
            delay: Seconds to wait between requests (be respectful)
        """
        self.vendor_config = vendor_config
        self.delay = delay
        
        # Extract vendor info
        self.vendor_name = vendor_config.get('name', 'Unknown')
        self.base_url = vendor_config.get('website', '').rstrip('/')
        
        # Scraper configuration
        self.scraper_config = vendor_config.get('scraper', {})
        
        # Link extraction patterns
        self.link_patterns = self.scraper_config.get('link_patterns', [])
        self.exclude_patterns = self.scraper_config.get('exclude_patterns', [])
        
        # Pagination configuration (if using pagination)
        self.pagination_config = self.scraper_config.get('pagination', {})
        self.discovery_fetch_method = self.scraper_config.get('discovery_fetch_method', 'auto').lower()
        
        # Initialize Scrapy scraper (first attempt - free)
        self.scrapy_scraper = None
        if SCRAPY_AVAILABLE:
            try:
                self.scrapy_scraper = ScrapyScraper(delay=delay)
            except Exception as e:
                print(f"  ⚠ Scrapy not available: {e}")
        
        # Initialize HyperBrowser.ai client (fallback - paid)
        self.hb_client = None
        self.session_id = None
        
        if HYPERBROWSER_AVAILABLE:
            api_key = os.getenv('HYPERBROWSER_API_KEY')
            if api_key:
                try:
                    self.hb_client = Hyperbrowser(api_key=api_key)
                    self._close_active_sessions()
                    if self.pagination_config.get('create_session', False):
                        self._create_session()
                except Exception as e:
                    print(f"  ⚠ HyperBrowser.ai not available: {e}")
        
        if not self.scrapy_scraper and not self.hb_client:
            raise RuntimeError(
                f"Neither Scrapy nor HyperBrowser.ai is available for {self.vendor_name}. "
                f"Install at least one: pip install scrapy or pip install hyperbrowser"
            )
    
    def _close_active_sessions(self):
        """Close any active HyperBrowser.ai sessions to avoid session limit errors."""
        if not self.hb_client:
            return
        
        try:
            sessions_response = self.hb_client.sessions.list()
            closed_count = 0
            for session in sessions_response.sessions:
                if session.status == 'active':
                    try:
                        self.hb_client.sessions.stop(session.id)
                        closed_count += 1
                    except Exception:
                        pass
            if closed_count > 0:
                print(f"  Closed {closed_count} active session(s)")
        except Exception:
            pass
    
    def _create_session(self):
        """Create a single session to reuse for all scrape requests."""
        if not self.hb_client:
            return
        
        try:
            session_response = self.hb_client.sessions.create(SessionCreateParams())
            self.session_id = session_response.id
        except Exception as e:
            self.session_id = None
    
    def _ensure_session_active(self):
        """Ensure we have an active session, track it if HyperBrowser creates one."""
        if not self.hb_client:
            return
        
        try:
            sessions_response = self.hb_client.sessions.list()
            active_sessions = [s for s in sessions_response.sessions if s.status == 'active']
            
            if active_sessions:
                if not self.session_id:
                    self.session_id = active_sessions[0].id
                elif len(active_sessions) > 1:
                    for session in active_sessions:
                        if session.id != self.session_id:
                            try:
                                self.hb_client.sessions.stop(session.id)
                            except Exception:
                                pass
        except Exception:
            pass
    
    def _extract_links(self, html_content: str, base_url: str) -> Set[str]:
        """
        Extract customer reference URLs from HTML using configured patterns.
        
        Args:
            html_content: Raw HTML string
            base_url: Base URL for resolving relative links
            
        Returns:
            Set of customer reference URLs
        """
        links = set()
        
        # Find all href attributes
        href_pattern = r'href=["\']([^"\']+)["\']'
        hrefs = re.findall(href_pattern, html_content, re.IGNORECASE)
        
        for href in hrefs:
            href_lower = href.lower()
            
            # Check if href matches any include pattern
            matches_pattern = False
            if self.link_patterns:
                for pattern in self.link_patterns:
                    if pattern.lower() in href_lower:
                        matches_pattern = True
                        break
            else:
                # Default: look for common patterns
                if any(p in href_lower for p in ['/customers/', '/case-study/', '/customer-story/']):
                    matches_pattern = True
            
            if not matches_pattern:
                continue
            
            # Check if href matches any exclude pattern
            if self.exclude_patterns:
                if any(pattern.lower() in href_lower for pattern in self.exclude_patterns):
                    continue
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Additional validation: ensure URL has content after the pattern
            parts = [part for part in href.split('/') if part]
            if len(parts) <= 1:
                continue

            # Skip links that end at the include pattern itself (e.g., '/customers/')
            last_segment = parts[-1]
            if last_segment.lower() in {'customers', 'customer-case-studies', 'case-study', 'case-studies'}:
                continue

            links.add(full_url)
        
        json_paths = re.findall(r'\\"pathname\\":\\"(/[^\\"\s]+)\\"', html_content)
        for path in json_paths:
            path_lower = path.lower()
            if self.link_patterns and not any(pattern.lower() in path_lower for pattern in self.link_patterns):
                continue
            if any(pattern.lower() in path_lower for pattern in self.exclude_patterns):
                continue
            parts = [part for part in path.split('/') if part]
            if len(parts) <= 1:
                continue
            last_segment = parts[-1]
            if last_segment.lower() in {'customers', 'customer-case-studies', 'case-study', 'case-studies'}:
                continue
            links.add(urljoin(base_url, path))

        return links
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page using Scrapy first, then HyperBrowser.ai as fallback.
        
        Args:
            url: URL to fetch
            
        Returns:
            Raw HTML string or None
        """
        # Optional direct requests fetch (useful for static Next.js pages)
        if self.discovery_fetch_method == 'requests':
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/120.0.0.0 Safari/537.36'
                }
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.ok and resp.text:
                    return resp.text
            except Exception:
                pass
        
        # Try Scrapy first (free, fast)
        if self.scrapy_scraper:
            result = self.scrapy_scraper.scrape_url(url)
            if result and result.get('html'):
                html_content = result['html']
                # Check for anti-bot indicators
                html_lower = html_content.lower()
                if not any(indicator in html_lower for indicator in self.BLOCK_INDICATORS):
                    if len(html_content) >= 500:
                        return html_content
        
        # Fallback to HyperBrowser.ai
        return self._fetch_page_with_hyperbrowser(url)
    
    def _fetch_page_with_hyperbrowser(self, url: str) -> Optional[str]:
        """
        Fetch a page using HyperBrowser.ai.
        
        Args:
            url: URL to fetch
            
        Returns:
            Raw HTML string or None
        """
        if not self.hb_client:
            return None
        
        try:
            self._ensure_session_active()
            
            result = self.hb_client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url=url,
                    scrape_options=ScrapeOptions(
                        formats=["html", "markdown"],
                        only_main_content=False
                    )
                )
            )
            
            # Check for errors
            if hasattr(result, 'status') and result.status == 'failed':
                return None
            
            # Extract HTML content
            html_content = None
            if hasattr(result, 'data') and result.data:
                if hasattr(result.data, 'html') and result.data.html:
                    html_content = result.data.html
                elif hasattr(result.data, 'markdown') and result.data.markdown:
                    html_content = result.data.markdown
            
            return html_content
            
        except Exception:
            return None
    
    def get_customer_reference_urls(self, max_pages: Optional[int] = None) -> List[str]:
        """
        Get list of customer reference URLs using configured discovery method.
        
        Args:
            max_pages: Maximum number of pages to scrape (for pagination)
            
        Returns:
            List of full URLs to customer reference pages
        """
        discovery_method = self.vendor_config.get('discovery_method', 'sitemap')
        
        if discovery_method == 'pagination':
            return self._discover_via_pagination(max_pages)
        else:
            # Sitemap discovery is handled by pipeline runner
            # This method shouldn't be called for sitemap-based vendors
            raise NotImplementedError(
                f"URL discovery for {self.vendor_name} uses sitemap, "
                f"not pagination. Use sitemap_discovery utility instead."
            )
    
    def _discover_via_pagination(self, max_pages: Optional[int] = None) -> List[str]:
        """
        Discover URLs using pagination.
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of customer reference URLs
        """
        pagination_path = self.pagination_config.get('path', '/customers/')
        strategy_type = self.pagination_config.get('strategy', 'offset')
        
        # Build pagination strategy
        if strategy_type == 'offset':
            strategy = OffsetPaginationStrategy(
                pagination_path=pagination_path,
                page_param=self.pagination_config.get('page_param', 'page'),
                page_size_param=self.pagination_config.get('page_size_param', 'pageSize'),
                offset_param=self.pagination_config.get('offset_param', 'offset')
            )
        else:  # page_number
            strategy = PageNumberPaginationStrategy(
                pagination_path=pagination_path,
                page_param=self.pagination_config.get('page_param', 'page')
            )
        
        # Configure pagination behavior
        config = PaginationConfig(
            page_size=self.pagination_config.get('page_size', 12),
            max_pages=max_pages,
            max_consecutive_empty=self.pagination_config.get('max_consecutive_empty', 2),
            check_duplicates=True,
            check_empty_pages=True
        )
        
        # Use generic pagination function
        urls = paginate_with_strategy(
            strategy=strategy,
            link_extractor=self._extract_links,
            page_fetcher=self._fetch_page,
            base_url=self.base_url,
            config=config,
            verbose=True
        )
        
        return list(urls)
    
    def _scrape_with_scrapy(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape using Scrapy (first attempt).
        
        Args:
            url: URL to scrape
            
        Returns:
            Dict with scraped data or None if failed
        """
        if not self.scrapy_scraper:
            return None
        
        try:
            result = self.scrapy_scraper.scrape_reference(url)
            return result
        except Exception:
            return None
    
    def _scrape_with_hyperbrowser(self, url: str) -> Dict[str, Any]:
        """
        Scrape using HyperBrowser.ai (fallback).
        
        Args:
            url: URL to scrape
            
        Returns:
            Dict with scraped data
        """
        if not self.hb_client:
            raise Exception("HyperBrowser.ai client not available")
        
        try:
            self._ensure_session_active()
            
            result = self.hb_client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url=url,
                    scrape_options=ScrapeOptions(
                        formats=["markdown", "html"],
                        only_main_content=False,
                        exclude_tags=["nav", "footer", "header", "script", "style"]
                    )
                )
            )
            
            # Check for errors
            if hasattr(result, 'status') and result.status == 'failed':
                error_msg = getattr(result, 'error', 'Unknown error')
                raise Exception(f"HyperBrowser.ai failed: {error_msg}")
            
            # Extract content
            if hasattr(result, 'data'):
                if hasattr(result.data, 'markdown') and result.data.markdown:
                    raw_text = result.data.markdown
                elif hasattr(result.data, 'html') and result.data.html:
                    raw_text = result.data.html
                else:
                    raise Exception("No content extracted from HyperBrowser.ai result")
            else:
                raise Exception("Unexpected HyperBrowser.ai response structure")
            
            if not raw_text:
                raise Exception("No content extracted from HyperBrowser.ai result")
            
            # Extract customer name from text or URL
            customer_name = self._extract_customer_name(raw_text, url)
            
            # Clean up text
            lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
            raw_text = '\n'.join(lines)
            
            word_count = len(raw_text.split())
            
            return {
                'url': url,
                'customer_name': customer_name,
                'raw_text': raw_text,
                'scraped_date': datetime.now().isoformat(),
                'word_count': word_count,
                'method': 'hyperbrowser'
            }
            
        except Exception as e:
            raise Exception(f"HyperBrowser.ai failed: {e}")
    
    def _extract_customer_name(self, text: str, url: str) -> str:
        """
        Extract customer name from text or URL.
        
        Args:
            text: Scraped text content
            url: URL of the page
            
        Returns:
            Customer name or "Unknown"
        """
        # Try to extract from text first
        lines = text.split('\n')
        for line in lines[:15]:
            line = line.strip()
            # Markdown h1
            if line.startswith('# '):
                return line[2:].strip()
            # Look for company names in title-like lines
            elif len(line) > 5 and len(line) < 100:
                if any(word in line.lower() for word in ['uses', 'with', 'customer', 'case study', 'success', 'story']):
                    parts = re.split(r'\s+(?:uses|with|customer|case study|success|story)', line, flags=re.IGNORECASE)
                    if parts and parts[0]:
                        potential_name = parts[0].strip()
                        if len(potential_name) > 3 and len(potential_name) < 50:
                            return potential_name
        
        # Fallback: extract from URL
        url_parts = url.split('/')
        
        # Look for common patterns in URL
        for part in reversed(url_parts):
            if part and part not in ['customers', 'customer-case-studies', 'case-study', 'case-studies',
                                    'customers', 'all-customers', 'video', 'en', 'https:', 'http:', '', 'www']:
                # Skip language codes
                if part in ['de', 'fr', 'it', 'jp', 'kr', 'br']:
                    continue
                # Skip common non-company segments
                if part in ['gen-ai', 'your-ai', 'champions-program']:
                    continue
                
                potential_name = part.replace('-', ' ').title()
                if len(potential_name) > 2:
                    return potential_name
        
        return "Unknown"
    
    def scrape_reference(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single customer reference page.
        Tries Scrapy first (free), then falls back to HyperBrowser.ai.
        
        Args:
            url: URL of customer reference page
            
        Returns:
            Dict with raw_text, url, customer_name, scraped_date, word_count
        """
        if self.scrapy_scraper:
            result = self._scrape_with_scrapy(url)
            if result and result.get('word_count', 0) >= 100:  # Valid result
                print(f"    → Scraped via Scrapy: {url}")
                return result
        
        # Fallback to HyperBrowser.ai
        if not self.hb_client:
            return None
        
        try:
            result = self._scrape_with_hyperbrowser(url)
            if result:
                print(f"    → Scraped via HyperBrowser.ai: {url}")
            return result
        except Exception:
            return None

