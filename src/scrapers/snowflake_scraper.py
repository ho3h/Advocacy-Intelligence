"""Scraper for Snowflake customer references with BeautifulSoup and HyperBrowser.ai fallback."""

import requests
from bs4 import BeautifulSoup
import time
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

# Try to import HyperBrowser.ai (optional dependency)
try:
    from hyperbrowser import Hyperbrowser
    from hyperbrowser.models import StartScrapeJobParams, ScrapeOptions, CreateSessionParams
    HYPERBROWSER_AVAILABLE = True
except ImportError:
    HYPERBROWSER_AVAILABLE = False


class SnowflakeScraper:
    """Scrape customer references from Snowflake website.
    
    Uses HyperBrowser.ai directly since BeautifulSoup always gets blocked.
    All pages require JavaScript rendering to load content.
    """
    
    BASE_URL = "https://www.snowflake.com"
    CUSTOMERS_PAGE = "/en/why-snowflake/customers/"  # Main customers page
    ALL_CUSTOMERS_BASE = "/en/customers/all-customers/"  # Paginated listing page
    
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
    
    def __init__(self, delay=2, use_hyperbrowser_fallback=True):
        """
        Initialize scraper.
        
        Args:
            delay: Seconds to wait between requests (be respectful)
            use_hyperbrowser_fallback: If True, fall back to HyperBrowser.ai on failure
        """
        self.delay = delay
        self.use_hyperbrowser_fallback = use_hyperbrowser_fallback
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Initialize HyperBrowser.ai client if available and enabled
        self.hb_client = None
        if use_hyperbrowser_fallback and HYPERBROWSER_AVAILABLE:
            api_key = os.getenv('HYPERBROWSER_API_KEY')
            if api_key:
                try:
                    self.hb_client = Hyperbrowser(api_key=api_key)
                    print("✓ HyperBrowser.ai fallback enabled")
                except Exception as e:
                    print(f"⚠ Failed to initialize HyperBrowser.ai: {e}")
                    print("  Continuing with BeautifulSoup only")
            else:
                print("⚠ HYPERBROWSER_API_KEY not found in environment")
                print("  Continuing with BeautifulSoup only")
    
    def _extract_case_study_links(self, soup, base_url):
        """
        Extract case study and video URLs from a BeautifulSoup parsed page.
        Excludes the listing page itself and filters out invalid URLs.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            Set of case study and video URLs
        """
        links = set()
        customer_links = soup.find_all('a', href=True)
        
        for link in customer_links:
            href = link['href']
            href_lower = href.lower()
            
            # Only include URLs that are actual case studies or videos
            # Must contain /case-study/ or /video/ in the path
            is_case_study = '/case-study/' in href_lower
            is_video = '/video/' in href_lower
            
            if is_case_study or is_video:
                # Exclude the base listing page
                if href_lower not in ['/en/customers/all-customers/', '/customers/all-customers/']:
                    # Ensure URL has a company name after /case-study/ or /video/
                    # Valid: /case-study/company-name/ or /video/company-name/
                    # Invalid: /case-study/ or /video/ (no company name)
                    parts = href.split('/')
                    if is_case_study:
                        case_study_idx = [i for i, p in enumerate(parts) if 'case-study' in p.lower()]
                        if case_study_idx and case_study_idx[0] + 1 < len(parts) and parts[case_study_idx[0] + 1]:
                            full_url = urljoin(base_url, href)
                            links.add(full_url)
                    elif is_video:
                        video_idx = [i for i, p in enumerate(parts) if 'video' in p.lower()]
                        if video_idx and video_idx[0] + 1 < len(parts) and parts[video_idx[0] + 1]:
                            full_url = urljoin(base_url, href)
                            links.add(full_url)
        
        return links
    
    def _fetch_page_with_hyperbrowser(self, url):
        """
        Fetch a page using HyperBrowser.ai.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None
        """
        if not self.hb_client:
            return None
        
        try:
            from hyperbrowser.models import StartScrapeJobParams, ScrapeOptions, CreateSessionParams
            
            result = self.hb_client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url=url,
                    scrape_options=ScrapeOptions(
                        formats=["html", "markdown"],
                        only_main_content=False
                    ),
                    session_options=CreateSessionParams(
                        use_stealth=True,
                        accept_cookies=True
                    )
                )
            )
            
            # Parse the HTML result
            html_content = None
            if hasattr(result, 'data'):
                if hasattr(result.data, 'html') and result.data.html:
                    html_content = result.data.html
                elif hasattr(result.data, 'markdown') and result.data.markdown:
                    html_content = result.data.markdown
            
            if html_content:
                return BeautifulSoup(html_content, 'html.parser')
            return None
            
        except Exception as e:
            print(f"  ✗ HyperBrowser.ai failed: {e}")
            return None
    
    def get_customer_reference_urls(self, max_pages=5):
        """
        Get list of customer reference URLs from paginated all-customers pages.
        Uses HyperBrowser.ai directly since BeautifulSoup always gets blocked.
        
        Args:
            max_pages: Maximum number of paginated pages to scrape (default: 5)
        
        Returns:
            List of full URLs to customer reference pages
        """
        print(f"Fetching customer case studies from paginated listing pages...")
        
        if not self.hb_client:
            print("✗ HyperBrowser.ai not available - cannot fetch URLs (BeautifulSoup always blocked)")
            return []
        
        all_case_study_urls = set()
        page_size = 12
        
        # Fetch paginated pages using HyperBrowser.ai (BeautifulSoup always gets blocked)
        for page_num in range(max_pages):
            offset = page_num * page_size
            paginated_url = f"{self.BASE_URL}{self.ALL_CUSTOMERS_BASE}?page={page_num}&pageSize={page_size}&offset={offset}"
            
            print(f"  Fetching page {page_num + 1} (offset {offset}) with HyperBrowser.ai...")
            
            soup = self._fetch_page_with_hyperbrowser(paginated_url)
            
            if soup:
                # Extract case study links from this page
                page_links = self._extract_case_study_links(soup, self.BASE_URL)
                all_case_study_urls.update(page_links)
                print(f"    ✓ Found {len(page_links)} case study URLs on this page")
                
                # If no links found, we might have reached the end
                if len(page_links) == 0:
                    print(f"    No more case studies found, stopping pagination")
                    break
            else:
                print(f"    ✗ Could not parse page, skipping")
                break
        
        all_case_study_urls = sorted(list(all_case_study_urls))
        print(f"\n✓ Found {len(all_case_study_urls)} total case study URLs")
        return all_case_study_urls[:25]  # Limit to 25 for initial test
    
    def _is_blocked(self, soup, response_text=None):
        """
        Check if the page appears to be blocked by anti-bot protection.
        
        Args:
            soup: BeautifulSoup object
            response_text: Raw response text (optional)
            
        Returns:
            True if page appears blocked
        """
        if response_text is None:
            response_text = str(soup).lower()
        else:
            response_text = response_text.lower()
        
        # Check for common block indicators
        for indicator in self.BLOCK_INDICATORS:
            if indicator in response_text:
                return True
        
        # Check if page is suspiciously short (likely a block page)
        text_content = soup.get_text()
        if len(text_content.strip()) < 200:  # Very short content
            # Check if it's just navigation/header/footer
            main_content_tags = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and ('content' in x.lower() or 'main' in x.lower()))
            if not main_content_tags:
                return True
        
        return False
    
    def _parse_with_beautifulsoup(self, soup, url):
        """
        Parse content using BeautifulSoup.
        
        Args:
            soup: BeautifulSoup object
            url: Source URL
            
        Returns:
            Dict with scraped data
        """
        # Extract customer name (usually in title or h1)
        customer_name = "Unknown"
        title_tag = soup.find('h1')
        if title_tag:
            customer_name = title_tag.get_text(strip=True)
        
        # Extract main content text
        # Remove nav, footer, scripts, styles
        for tag in soup(['nav', 'footer', 'script', 'style', 'header']):
            tag.decompose()
        
        # Get clean text
        raw_text = soup.get_text(separator='\n', strip=True)
        
        # Clean up multiple newlines
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        raw_text = '\n'.join(lines)
        
        word_count = len(raw_text.split())
        
        return {
            'url': url,
            'customer_name': customer_name,
            'raw_text': raw_text,
            'scraped_date': datetime.now().isoformat(),
            'word_count': word_count,
            'method': 'beautifulsoup'
        }
    
    def _scrape_with_hyperbrowser(self, url):
        """
        Scrape using HyperBrowser.ai as fallback.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dict with scraped data
        """
        if not self.hb_client:
            raise Exception("HyperBrowser.ai client not available")
        
        print(f"  → Using HyperBrowser.ai fallback (this may take 10-30 seconds)...")
        
        try:
            result = self.hb_client.scrape.start_and_wait(
                StartScrapeJobParams(
                    url=url,
                    scrape_options=ScrapeOptions(
                        formats=["markdown", "html"],
                        only_main_content=False,  # Get all content, not just main - some pages need this
                        exclude_tags=["nav", "footer", "header", "script", "style"]
                    ),
                    session_options=CreateSessionParams(
                        use_stealth=True,
                        accept_cookies=True
                    )
                )
            )
            
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
                    if any(word in line.lower() for word in ['uses', 'with', 'customer', 'case study', 'success']):
                        # Extract company name (usually before "uses" or "with")
                        parts = re.split(r'\s+(?:uses|with|customer|case study|success)', line, flags=re.IGNORECASE)
                        if parts and parts[0]:
                            potential_name = parts[0].strip()
                            if len(potential_name) > 3 and len(potential_name) < 50:
                                customer_name = potential_name
                                break
            
            # Fallback: try to extract from URL (case-study URLs have company name at the end)
            if customer_name == "Unknown":
                url_parts = url.split('/')
                # Look for company name in case-study URLs: .../case-study/{company}/
                if '/case-study/' in url:
                    case_study_idx = url_parts.index('case-study') if 'case-study' in url_parts else -1
                    if case_study_idx >= 0 and case_study_idx + 1 < len(url_parts):
                        company_part = url_parts[case_study_idx + 1]
                        if company_part:
                            customer_name = company_part.replace('-', ' ').title()
                else:
                    # Fallback: look for company-like segments in URL
                    for part in reversed(url_parts):
                        if part and part not in ['customers', 'all-customers', 'video', 'case-study', 'en', 'www.snowflake.com', 'https:', '']:
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
        Uses HyperBrowser.ai directly since BeautifulSoup always gets blocked.
        
        Args:
            url: URL of customer reference page
            
        Returns:
            Dict with raw_text, url, customer_name, scraped_date, word_count
        """
        print(f"  Scraping: {url[:60]}...")
        
        # BeautifulSoup always gets blocked, so use HyperBrowser.ai directly
        if not self.hb_client:
            print(f"  ✗ HyperBrowser.ai not available (required - BeautifulSoup always blocked)")
            return None
        
        try:
            result = self._scrape_with_hyperbrowser(url)
            print(f"  ✓ Scraped with HyperBrowser.ai ({result['word_count']} words)")
            return result
        except Exception as hb_error:
            print(f"  ✗ HyperBrowser.ai failed: {hb_error}")
            return None
    
    def scrape_all(self):
        """
        Scrape all customer references.
        Filters out invalid URLs and low-quality scrapes.
        
        Returns:
            List of reference dicts
        """
        urls = self.get_customer_reference_urls()
        references = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}]")
            
            # Filter out invalid URLs (must be case-study or video with company name)
            url_lower = url.lower()
            if not ('/case-study/' in url_lower or '/video/' in url_lower):
                print(f"  ⚠ Skipping invalid URL (not a case study or video): {url}")
                continue
            
            # Skip the base listing page
            if url_lower.endswith('/all-customers/') or url_lower.endswith('/all-customers'):
                print(f"  ⚠ Skipping listing page: {url}")
                continue
            
            ref_data = self.scrape_reference(url)
            if ref_data:
                # Filter out low-quality scrapes (too short, likely failed)
                if ref_data['word_count'] < 100:
                    print(f"  ⚠ Skipping low-quality scrape ({ref_data['word_count']} words): {url}")
                    continue
                
                references.append(ref_data)
                method = ref_data.get('method', 'unknown')
                print(f"✓ Scraped {ref_data['customer_name']} ({ref_data['word_count']} words) [{method}]")
            
            # Be respectful - wait between requests
            if i < len(urls):
                time.sleep(self.delay)
        
        print(f"\n✓ Scraped {len(references)} references")
        return references


if __name__ == '__main__':
    # Test scraper
    scraper = SnowflakeScraper()
    references = scraper.scrape_all()
    
    # Show sample
    if references:
        print("\nSample reference:")
        sample = references[0]
        print(f"Customer: {sample['customer_name']}")
        print(f"URL: {sample['url']}")
        print(f"Text preview: {sample['raw_text'][:200]}...")

