"""Scraper for MongoDB customer references using HyperBrowser.ai."""

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

load_dotenv()

# Try to import HyperBrowser.ai (required dependency)
try:
    from hyperbrowser import Hyperbrowser
    from hyperbrowser.models import StartScrapeJobParams, ScrapeOptions
    from hyperbrowser.models.session import CreateSessionParams as SessionCreateParams
    HYPERBROWSER_AVAILABLE = True
except ImportError:
    HYPERBROWSER_AVAILABLE = False


class MongoDBScraper:
    """Scrape customer references from MongoDB website.
    
    Uses HyperBrowser.ai for all scraping. Handles JavaScript rendering and anti-bot protection.
    """
    
    BASE_URL = "https://www.mongodb.com"
    
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
    
    def _ensure_session_active(self):
        """Ensure we have an active session, track it if HyperBrowser creates one."""
        try:
            sessions_response = self.hb_client.sessions.list()
            active_sessions = [s for s in sessions_response.sessions if s.status == 'active']
            
            if active_sessions:
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
        except Exception:
            pass
    
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
        
        if not TQDM_AVAILABLE:
            print(f"  → Fetching with HyperBrowser.ai (10-30 seconds)...", flush=True)
        
        try:
            self._ensure_session_active()
            
            start_time = time.time()
            
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
            
            elapsed = time.time() - start_time
            
            # Check for errors
            if hasattr(result, 'status') and result.status == 'failed':
                error_msg = getattr(result, 'error', 'Unknown error')
                raise Exception(f"HyperBrowser.ai failed: {error_msg}")
            
            # Extract content from result
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
            
            # Extract customer name from text or URL
            customer_name = "Unknown"
            lines = raw_text.split('\n')
            
            # Try multiple patterns for customer name
            for line in lines[:15]:  # Check first 15 lines
                line = line.strip()
                # Markdown h1
                if line.startswith('# '):
                    customer_name = line[2:].strip()
                    break
                # Look for company names in title-like lines
                elif len(line) > 5 and len(line) < 100:
                    if any(word in line.lower() for word in ['uses', 'with', 'customer', 'case study', 'success', 'story']):
                        parts = re.split(r'\s+(?:uses|with|customer|case study|success|story)', line, flags=re.IGNORECASE)
                        if parts and parts[0]:
                            potential_name = parts[0].strip()
                            if len(potential_name) > 3 and len(potential_name) < 50:
                                customer_name = potential_name
                                break
            
            # Fallback: try to extract from URL
            if customer_name == "Unknown":
                url_parts = url.split('/')
                # MongoDB URLs: /customers/{name} or /solutions/customer-case-studies/{name}
                if '/customers/' in url:
                    customers_idx = url_parts.index('customers') if 'customers' in url_parts else -1
                    if customers_idx >= 0 and customers_idx + 1 < len(url_parts):
                        company_part = url_parts[customers_idx + 1]
                        if company_part:
                            customer_name = company_part.replace('-', ' ').title()
                elif '/customer-case-studies/' in url:
                    case_studies_idx = url_parts.index('customer-case-studies') if 'customer-case-studies' in url_parts else -1
                    if case_studies_idx >= 0 and case_studies_idx + 1 < len(url_parts):
                        company_part = url_parts[case_studies_idx + 1]
                        if company_part:
                            customer_name = company_part.replace('-', ' ').title()
                else:
                    # Fallback: look for company-like segments in URL
                    for part in reversed(url_parts):
                        if part and part not in ['customers', 'customer-case-studies', 'mongodb.com', 'www', 'https:', '']:
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
        if not self.hb_client:
            print(f"  ✗ HyperBrowser.ai not available (required)", flush=True)
            return None
        
        try:
            result = self._scrape_with_hyperbrowser(url)
            return result
        except Exception as hb_error:
            if not TQDM_AVAILABLE:
                print(f"  ✗ HyperBrowser.ai failed: {hb_error}", flush=True)
            return None


if __name__ == '__main__':
    # Test scraper
    scraper = MongoDBScraper()
    test_url = "https://www.mongodb.com/customers/apna"
    print(f"Testing scraper with: {test_url}")
    result = scraper.scrape_reference(test_url)
    if result:
        print(f"\n✓ Successfully scraped:")
        print(f"  Customer: {result['customer_name']}")
        print(f"  Word count: {result['word_count']}")
        print(f"  Content preview: {result['raw_text'][:200]}...")

