"""Scraper for Redis customer references using HyperBrowser.ai."""

import time
import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin
from dotenv import load_dotenv

# Try to import tqdm for progress bars (optional)
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Import pagination utilities
from scrapers.pagination import (
    PaginationConfig,
    OffsetPaginationStrategy,
    PageNumberPaginationStrategy,
    paginate_with_strategy
)

load_dotenv()

# Try to import HyperBrowser.ai (required dependency)
try:
    from hyperbrowser import Hyperbrowser
    from hyperbrowser.models import StartScrapeJobParams, ScrapeOptions
    from hyperbrowser.models.session import CreateSessionParams as SessionCreateParams
    HYPERBROWSER_AVAILABLE = True
except ImportError:
    HYPERBROWSER_AVAILABLE = False


class RedisScraper:
    """Scrape customer references from Redis website.
    
    Uses HyperBrowser.ai for all scraping. All pages require JavaScript rendering.
    """
    
    BASE_URL = "https://redis.io"
    CUSTOMERS_PAGE = "/customers/"  # Main customers page
    
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
    
    def __init__(self, delay=2):
        """
        Initialize scraper.
        
        Args:
            delay: Seconds to wait between requests (be respectful)
        """
        self.delay = delay
        
        # Initialize HyperBrowser.ai client (required)
        self.hb_client = None
        self.session_id = None  # Single session to reuse for all requests
        
        if not HYPERBROWSER_AVAILABLE:
            raise ImportError("HyperBrowser.ai is required but not installed. Install with: pip install hyperbrowser")
        
        api_key = os.getenv('HYPERBROWSER_API_KEY')
        if not api_key:
            raise ValueError("HYPERBROWSER_API_KEY not found in environment variables")
        
        try:
            self.hb_client = Hyperbrowser(api_key=api_key)
            # Close any existing active sessions to avoid "maximum sessions" error
            self._close_active_sessions()
            # Don't create a session upfront - let HyperBrowser create one on first request
            # We'll track it and reuse it
            print("✓ HyperBrowser.ai initialized")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize HyperBrowser.ai: {e}")
    
    def _close_active_sessions(self):
        """Close any active HyperBrowser.ai sessions to avoid session limit errors."""
        try:
            sessions_response = self.hb_client.sessions.list()
            closed_count = 0
            for session in sessions_response.sessions:
                if session.status == 'active':
                    try:
                        self.hb_client.sessions.stop(session.id)
                        closed_count += 1
                    except Exception:
                        pass  # Ignore errors closing sessions
            if closed_count > 0:
                print(f"  Closed {closed_count} active session(s)")
        except Exception:
            pass  # Ignore errors listing sessions
    
    def _create_session(self):
        """Create a single session to reuse for all scrape requests."""
        try:
            # Create a new session
            session_response = self.hb_client.sessions.create(SessionCreateParams())
            self.session_id = session_response.id  # SessionDetail object has .id directly
            print(f"  Created session: {self.session_id[:8]}...")
        except Exception as e:
            print(f"  ⚠ Warning: Could not create session: {e}")
            print(f"  Will attempt to use existing sessions")
            self.session_id = None
    
    def _stop_session(self):
        """Stop the active session."""
        if self.session_id and self.hb_client:
            try:
                self.hb_client.sessions.stop(self.session_id)
                self.session_id = None
            except Exception:
                pass  # Ignore errors stopping session
    
    def _ensure_session_active(self):
        """Ensure we have an active session, track it if HyperBrowser creates one."""
        # Check for active sessions and track the first one
        try:
            sessions_response = self.hb_client.sessions.list()
            active_sessions = [s for s in sessions_response.sessions if s.status == 'active']
            
            if active_sessions:
                # Track the first active session
                if not self.session_id:
                    self.session_id = active_sessions[0].id
                    print(f"  ✓ Tracking existing session: {self.session_id[:8]}...", flush=True)
                elif len(active_sessions) > 1:
                    # Multiple active sessions - close extras, keep only ours
                    for session in active_sessions:
                        if session.id != self.session_id:
                            try:
                                self.hb_client.sessions.stop(session.id)
                                print(f"  ⚠ Closed extra session {session.id[:8]}...", flush=True)
                            except Exception:
                                pass
            # If no active sessions, HyperBrowser will create one on the next request
            # We'll track it after the first request completes
        except Exception:
            # If we can't check, that's okay - HyperBrowser will handle it
            pass
    
    def _extract_customer_story_links(self, html_content, base_url):
        """
        Extract customer story URLs from raw HTML content using regex.
        
        Args:
            html_content: Raw HTML string
            base_url: Base URL for resolving relative links
            
        Returns:
            Set of customer story URLs
        """
        links = set()
        
        # Find all href attributes in anchor tags
        href_pattern = r'href=["\']([^"\']+)["\']'
        hrefs = re.findall(href_pattern, html_content, re.IGNORECASE)
        
        for href in hrefs:
            href_lower = href.lower()
            
            # Redis customer stories are typically at /customers/{customer-name}/
            # or might be in a different format - we'll need to check the actual page structure
            # Common patterns:
            # - /customers/{name}/
            # - /customers/{name}
            # - /customer-stories/{name}/
            # - Links containing "customer" and a company name
            
            # Look for customer story links
            # Pattern 1: /customers/{name} (not just /customers/)
            if '/customers/' in href_lower and href_lower != '/customers/' and not href_lower.endswith('/customers'):
                # Make sure it's not a filter or category link
                if not any(skip in href_lower for skip in ['?', '#', 'industry=', 'region=', 'filter=']):
                    # Exclude the base customers page
                    if href_lower not in ['/customers/', '/customers']:
                        full_url = urljoin(base_url, href)
                        # Make sure it's a customer story URL (has a company name after /customers/)
                        parts = href.split('/')
                        if 'customers' in parts:
                            customers_idx = parts.index('customers')
                            # Should have something after 'customers'
                            if customers_idx + 1 < len(parts) and parts[customers_idx + 1]:
                                links.add(full_url)
            
            # Pattern 2: /customer-stories/ or similar
            elif '/customer-stories/' in href_lower or '/customer-story/' in href_lower:
                full_url = urljoin(base_url, href)
                links.add(full_url)
        
        return links
    
    def _fetch_page_with_hyperbrowser(self, url):
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
            # Ensure our session is still active before scraping
            self._ensure_session_active()
            
            print(f"    → Fetching with HyperBrowser.ai (this may take 10-30 seconds)...", flush=True)
            start_time = time.time()
            
            # Don't pass session_options - HyperBrowser should automatically reuse our active session
            # We create ONE session at initialization, and HyperBrowser should reuse it automatically
            result = self.hb_client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url=url,
                    scrape_options=ScrapeOptions(
                        formats=["html", "markdown"],
                        only_main_content=False
                    )
                    # Don't pass session_options - HyperBrowser should reuse our active session automatically
                )
            )
            
            elapsed = time.time() - start_time
            
            # Check for errors
            if hasattr(result, 'status') and result.status == 'failed':
                error_msg = getattr(result, 'error', 'Unknown error')
                print(f"    ✗ HyperBrowser.ai failed: {error_msg}", flush=True)
                return None
            
            # Extract HTML content from result
            html_content = None
            if hasattr(result, 'data') and result.data:
                if hasattr(result.data, 'html') and result.data.html:
                    html_content = result.data.html
                elif hasattr(result.data, 'markdown') and result.data.markdown:
                    # Use markdown as fallback (can still extract links from it)
                    html_content = result.data.markdown
            
            if not html_content:
                print(f"    ⚠ No content extracted from HyperBrowser.ai (status: {getattr(result, 'status', 'unknown')})", flush=True)
                return None
            
            print(f"    ✓ Successfully fetched page ({len(html_content)} chars) in {elapsed:.1f}s", flush=True)
            return html_content
            
        except Exception as e:
            print(f"    ✗ HyperBrowser.ai error: {type(e).__name__}: {e}", flush=True)
            return None
    
    def _click_load_more_and_wait(self, url, max_clicks=50):
        """
        Click "load more" button repeatedly until all content is loaded.
        Uses HyperBrowser.ai computer_action.click to interact with the page.
        
        Args:
            url: URL to load
            max_clicks: Maximum number of "load more" clicks (safety limit)
        
        Returns:
            Final HTML content after all "load more" clicks
        """
        print("  🔄 Loading all content (may need multiple fetches for 'Load More')...", flush=True)
        
        # Don't create a session upfront - let HyperBrowser create one automatically
        # First, fetch the initial page
        print("    → Loading initial page...", flush=True)
        result = self.hb_client.scrape.start_and_wait(
            StartScrapeJobParams(
                url=url,
                scrape_options=ScrapeOptions(
                    formats=["html"],
                    only_main_content=False
                )
            )
        )
        
        # Track the session that was used/created
        self._ensure_session_active()
        
        if hasattr(result, 'status') and result.status == 'failed':
            error_msg = getattr(result, 'error', 'Unknown error')
            print(f"    ✗ Failed to load page: {error_msg}", flush=True)
            return None
        
        # Check for errors in result
        if hasattr(result, 'error'):
            print(f"    ✗ Error: {result.error}", flush=True)
            return None
        
        # Extract initial HTML
        html_content = None
        if hasattr(result, 'data') and result.data and hasattr(result.data, 'html'):
            html_content = result.data.html
        
        if not html_content:
            print("    ✗ No HTML content extracted", flush=True)
            return None
        
        all_links = self._extract_customer_story_links(html_content, self.BASE_URL)
        print(f"    ✓ Initial page: Found {len(all_links)} customer story links", flush=True)
        
        # Now scroll/click "load more" buttons repeatedly
        
        for click_num in range(max_clicks):
            # Find "load more" button using regex in HTML
            load_more_patterns = [
                r'<button[^>]*>.*?load\s+more.*?</button>',
                r'<a[^>]*>.*?load\s+more.*?</a>',
                r'<button[^>]*class="[^"]*load[^"]*more[^"]*"',
                r'<button[^>]*data-testid="[^"]*load[^"]*more[^"]*"',
            ]
            
            button_found = False
            button_text = None
            
            for pattern in load_more_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    button_found = True
                    # Extract button text
                    text_match = re.search(r'>([^<]*load\s+more[^<]*)<', match.group(0), re.IGNORECASE)
                    if text_match:
                        button_text = text_match.group(1).strip()
                    break
            
            if not button_found:
                # Try finding by text content in the HTML
                if re.search(r'load\s+more|show\s+more', html_content, re.IGNORECASE):
                    button_found = True
                    button_text = "Load More"
                else:
                    print(f"    ✓ No 'load more' button found (click {click_num}), all content loaded", flush=True)
                    break
            
            if button_found:
                print(f"    → Attempting to load more content (attempt {click_num + 1})...", flush=True)
                
                # Try scrolling to bottom to trigger "load more" (many sites load on scroll)
                try:
                    # Scroll down significantly to trigger load more
                    # scroll method signature: session, delta_x=0, delta_y=0
                    self.hb_client.computer_action.scroll(
                        session=self.session_id,
                        delta_y=2000  # Scroll down a lot
                    )
                    time.sleep(3)  # Wait for content to load
                    
                    # Re-fetch the page to get updated HTML
                    result = self.hb_client.scrape.start_and_wait(
                        StartScrapeJobParams(
                            url=url,
                            scrape_options=ScrapeOptions(
                                formats=["html"],
                                only_main_content=False
                            )
                        )
                    )
                    
                    # Track session again
                    self._ensure_session_active()
                    
                    if hasattr(result, 'data') and result.data and hasattr(result.data, 'html'):
                        html_content = result.data.html
                        current_links = self._extract_customer_story_links(html_content, self.BASE_URL)
                        new_links = current_links - all_links
                        
                        if new_links:
                            all_links.update(new_links)
                            print(f"    ✓ Found {len(new_links)} new links (total: {len(all_links)})", flush=True)
                        else:
                            print(f"    ⚠ No new links found after scroll {click_num + 1}", flush=True)
                            # Try clicking the button directly if scrolling didn't work
                            # We'd need button coordinates, which is complex
                            # For now, if no new links after 2 scrolls, assume we're done
                            if click_num >= 1:
                                break
                    else:
                        print(f"    ⚠ Could not get updated HTML after scroll", flush=True)
                        
                except Exception as e:
                    print(f"    ⚠ Error scrolling: {e}", flush=True)
                    # If scrolling fails, we can't interact with the page
                    break
        
        print(f"    ✓ Finished clicking. Total links found: {len(all_links)}", flush=True)
        return html_content
    
    def get_customer_reference_urls(self, max_pages=None):
        """
        Get list of customer reference URLs from Redis customers page.
        Uses HyperBrowser.ai for all scraping.
        
        Handles "load more" buttons to load all customer stories.
        
        Args:
            max_pages: Not used for Redis (uses "load more" instead)
        
        Returns:
            List of full URLs to customer reference pages
        """
        print("\n" + "=" * 70)
        print("PHASE 1: URL DISCOVERY")
        print("=" * 70)
        
        if not self.hb_client:
            print("✗ HyperBrowser.ai not available - cannot fetch URLs")
            return []
        
        print("🔍 Discovering customer reference URLs from Redis customers page...")
        print(f"📄 URL: {self.BASE_URL}{self.CUSTOMERS_PAGE}")
        print(f"⏱️  Estimated time: 5-10 minutes (clicking 'Load More' buttons)\n")
        
        start_time = time.time()
        
        # Fetch the main customers page and click "load more" until all content is loaded
        customers_url = urljoin(self.BASE_URL, self.CUSTOMERS_PAGE)
        
        # Use the load more functionality
        final_html = self._click_load_more_and_wait(customers_url, max_clicks=50)
        
        if not final_html:
            print("✗ Failed to fetch customers page")
            return []
        
        # Extract all customer story links from the final page
        all_links = self._extract_customer_story_links(final_html, self.BASE_URL)
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 70, flush=True)
        print("URL DISCOVERY SUMMARY", flush=True)
        print("=" * 70, flush=True)
        print(f"✓ Found {len(all_links)} unique customer reference URLs", flush=True)
        print(f"⏱️  Discovery time: {elapsed_time/60:.1f} minutes ({elapsed_time:.0f} seconds)", flush=True)
        print("=" * 70 + "\n", flush=True)
        
        return list(all_links)
    
    def _scrape_with_hyperbrowser(self, url):
        """
        Scrape using HyperBrowser.ai.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dict with scraped data
        """
        if not self.hb_client:
            raise Exception("HyperBrowser.ai client not available")
        
        # Don't print status if using tqdm (it handles progress display)
        if not TQDM_AVAILABLE:
            print(f"  → Fetching with HyperBrowser.ai (10-30 seconds)...", flush=True)
        
        try:
            # Ensure our session is still active before scraping
            self._ensure_session_active()
            
            start_time = time.time()
            
            # Don't pass session_options - HyperBrowser should automatically reuse our active session
            # If we pass session_options, it might create a new session
            result = self.hb_client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url=url,
                    scrape_options=ScrapeOptions(
                        formats=["markdown", "html"],
                        only_main_content=False,  # Get all content, not just main - some pages need this
                        exclude_tags=["nav", "footer", "header", "script", "style"]
                    )
                    # Don't pass session_options - HyperBrowser should reuse our active session automatically
                )
            )
            
            elapsed = time.time() - start_time
            
            # Check for errors
            if hasattr(result, 'status') and result.status == 'failed':
                error_msg = getattr(result, 'error', 'Unknown error')
                raise Exception(f"HyperBrowser.ai failed: {error_msg}")
            
            # Extract content from result
            scrape_result = result.scrape_result if hasattr(result, 'scrape_result') else result
            
            # Prefer markdown, fallback to html
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
            
            if not TQDM_AVAILABLE:
                print(f"  ✓ Fetched content ({len(raw_text)} chars) in {elapsed:.1f}s", flush=True)
            
            # Extract customer name from text (look for h1 or title patterns)
            customer_name = "Unknown"
            lines = raw_text.split('\n')
            
            # Try multiple patterns for customer name
            for line in lines[:15]:  # Check first 15 lines
                line = line.strip()
                # Markdown h1
                if line.startswith('# '):
                    customer_name = line[2:].strip()
                    break
                # Look for company names in title-like lines (all caps or title case)
                elif len(line) > 5 and len(line) < 100:
                    # Check if it looks like a company name (has common company words)
                    if any(word in line.lower() for word in ['uses', 'with', 'customer', 'case study', 'success', 'story']):
                        # Extract company name (usually before "uses" or "with")
                        parts = re.split(r'\s+(?:uses|with|customer|case study|success|story)', line, flags=re.IGNORECASE)
                        if parts and parts[0]:
                            potential_name = parts[0].strip()
                            if len(potential_name) > 3 and len(potential_name) < 50:
                                customer_name = potential_name
                                break
            
            # Fallback: try to extract from URL (customer URLs have company name)
            if customer_name == "Unknown":
                url_parts = url.split('/')
                # Look for company name in customer URLs: .../customers/{company}/
                if '/customers/' in url:
                    customers_idx = url_parts.index('customers') if 'customers' in url_parts else -1
                    if customers_idx >= 0 and customers_idx + 1 < len(url_parts):
                        company_part = url_parts[customers_idx + 1]
                        if company_part:
                            customer_name = company_part.replace('-', ' ').title()
                else:
                    # Fallback: look for company-like segments in URL
                    for part in reversed(url_parts):
                        if part and part not in ['customers', 'customer-stories', 'customer-story', 'redis.io', 'https:', '']:
                            # Clean up the part (remove hyphens, make title case)
                            potential_name = part.replace('-', ' ').title()
                            if len(potential_name) > 2:
                                customer_name = potential_name
                                break
            
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
            print(f"  ✗ HyperBrowser.ai failed: {e}")
            raise
    
    def scrape_reference(self, url):
        """
        Scrape a single customer reference page.
        Uses HyperBrowser.ai for all scraping.
        
        Args:
            url: URL of customer reference page
            
        Returns:
            Dict with raw_text, url, customer_name, scraped_date, word_count
        """
        # Use HyperBrowser.ai for all scraping
        if not self.hb_client:
            print(f"  ✗ HyperBrowser.ai not available (required)", flush=True)
            return None
        
        try:
            result = self._scrape_with_hyperbrowser(url)
            return result
        except Exception as hb_error:
            if not TQDM_AVAILABLE:  # Only print errors if not using tqdm (tqdm handles its own output)
                print(f"  ✗ HyperBrowser.ai failed: {hb_error}", flush=True)
            return None


if __name__ == '__main__':
    # Test scraper
    scraper = RedisScraper()
    urls = scraper.get_customer_reference_urls()
    
    # Show sample
    if urls:
        print(f"\nFound {len(urls)} customer reference URLs")
        print(f"\nSample URLs:")
        for url in list(urls)[:5]:
            print(f"  - {url}")

