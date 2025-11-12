"""Pagination utilities for vendor scrapers with flexible completion detection strategies."""

import sys
from typing import List, Set, Callable, Optional, Dict, Any, Tuple
from urllib.parse import urljoin


class PaginationConfig:
    """Configuration for pagination behavior."""
    
    def __init__(
        self,
        page_size: int = 12,
        max_consecutive_empty: int = 2,
        max_pages: Optional[int] = None,
        safety_limit: int = 100,
        check_duplicates: bool = True,
        check_empty_pages: bool = True,
        check_total_count: bool = False,
        total_count_selector: Optional[str] = None,
    ):
        """
        Initialize pagination configuration.
        
        Args:
            page_size: Number of items per page (for URL construction)
            max_consecutive_empty: Stop after N consecutive empty pages
            max_pages: Maximum pages to scrape (None = no limit)
            safety_limit: Absolute maximum pages (safety net)
            check_duplicates: Stop if all URLs on page are duplicates
            check_empty_pages: Stop after consecutive empty pages
            check_total_count: Try to detect total count from page
            total_count_selector: CSS selector or text pattern to find total count
        """
        self.page_size = page_size
        self.max_consecutive_empty = max_consecutive_empty
        self.max_pages = max_pages
        self.safety_limit = safety_limit
        self.check_duplicates = check_duplicates
        self.check_empty_pages = check_empty_pages
        self.check_total_count = check_total_count
        self.total_count_selector = total_count_selector


class PaginationStrategy:
    """Base class for pagination strategies."""
    
    def build_url(self, base_url: str, page_num: int, page_size: int) -> str:
        """
        Build pagination URL for a given page number.
        
        Args:
            base_url: Base URL or pagination endpoint
            page_num: Page number (0-indexed)
            page_size: Items per page
            
        Returns:
            Full URL for the page
        """
        raise NotImplementedError
    
    def extract_links(self, html_content: str, base_url: str) -> Set[str]:
        """
        Extract reference URLs from raw HTML content.
        
        Args:
            html_content: Raw HTML string
            base_url: Base URL for resolving relative links
            
        Returns:
            Set of reference URLs found on this page
        """
        raise NotImplementedError
    
    def should_stop(
        self,
        page_links: Set[str],
        all_links: Set[str],
        page_num: int,
        consecutive_empty: int,
        config: PaginationConfig,
        html_content: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Determine if pagination should stop.
        
        Args:
            page_links: Links found on current page
            all_links: All unique links found so far
            page_num: Current page number
            consecutive_empty: Number of consecutive empty pages
            config: Pagination configuration
            html_content: Raw HTML content (optional, for total count detection)
            
        Returns:
            Tuple of (should_stop: bool, reason: str)
        """
        # Check max pages limit
        if config.max_pages is not None and page_num >= config.max_pages:
            return True, f"Reached max_pages limit ({config.max_pages})"
        
        # Check safety limit
        if page_num >= config.safety_limit:
            return True, f"Safety limit: reached {config.safety_limit} pages"
        
        # Check for duplicates (if enabled)
        if config.check_duplicates and len(page_links) > 0:
            new_links = page_links - all_links
            if len(new_links) == 0:
                return True, "All URLs on this page were already seen (looped back)"
        
        # Check for empty pages (if enabled)
        if config.check_empty_pages:
            if len(page_links) == 0:
                if consecutive_empty >= config.max_consecutive_empty:
                    return True, f"Reached {config.max_consecutive_empty} consecutive empty pages"
            else:
                # Reset counter if we found links
                pass
        
        return False, ""


class OffsetPaginationStrategy(PaginationStrategy):
    """Pagination using offset/limit query parameters (e.g., ?page=0&pageSize=12&offset=0)."""
    
    def __init__(self, pagination_path: str, page_param: str = "page", page_size_param: str = "pageSize", offset_param: str = "offset"):
        """
        Initialize offset-based pagination.
        
        Args:
            pagination_path: Path to pagination endpoint (e.g., "/en/customers/all-customers/")
            page_param: Query parameter name for page number
            page_size_param: Query parameter name for page size
            offset_param: Query parameter name for offset
        """
        self.pagination_path = pagination_path
        self.page_param = page_param
        self.page_size_param = page_size_param
        self.offset_param = offset_param
    
    def build_url(self, base_url: str, page_num: int, page_size: int) -> str:
        """Build URL with offset-based pagination."""
        offset = page_num * page_size
        url = f"{base_url.rstrip('/')}{self.pagination_path}"
        params = [
            f"{self.page_param}={page_num}",
            f"{self.page_size_param}={page_size}",
            f"{self.offset_param}={offset}"
        ]
        return f"{url}?{'&'.join(params)}"


class PageNumberPaginationStrategy(PaginationStrategy):
    """Pagination using simple page number (e.g., ?page=1, ?page=2)."""
    
    def __init__(self, pagination_path: str, page_param: str = "page", start_at: int = 1):
        """
        Initialize page number-based pagination.
        
        Args:
            pagination_path: Path to pagination endpoint
            page_param: Query parameter name for page number
            start_at: First page number (usually 0 or 1)
        """
        self.pagination_path = pagination_path
        self.page_param = page_param
        self.start_at = start_at
    
    def build_url(self, base_url: str, page_num: int, page_size: int) -> str:
        """Build URL with page number pagination."""
        actual_page = page_num + self.start_at
        url = f"{base_url.rstrip('/')}{self.pagination_path}"
        return f"{url}?{self.page_param}={actual_page}"


class PathPaginationStrategy(PaginationStrategy):
    """Pagination using path segments (e.g., /page/1, /page/2)."""
    
    def __init__(self, pagination_path_template: str, start_at: int = 1):
        """
        Initialize path-based pagination.
        
        Args:
            pagination_path_template: Path template with {page} placeholder (e.g., "/customers/page/{page}")
            start_at: First page number (usually 0 or 1)
        """
        self.pagination_path_template = pagination_path_template
        self.start_at = start_at
    
    def build_url(self, base_url: str, page_num: int, page_size: int) -> str:
        """Build URL with path-based pagination."""
        actual_page = page_num + self.start_at
        path = self.pagination_path_template.format(page=actual_page)
        return f"{base_url.rstrip('/')}{path}"


def paginate_with_strategy(
    strategy: PaginationStrategy,
    link_extractor: Callable[[str, str], Set[str]],
    page_fetcher: Callable[[str], Optional[str]],
    base_url: str,
    config: PaginationConfig = PaginationConfig(),
    verbose: bool = True
) -> List[str]:
    """
    Generic pagination function that works with any pagination strategy.
    
    Args:
        strategy: Pagination strategy (defines URL building and link extraction)
        link_extractor: Function to extract links from raw HTML content
        page_fetcher: Function to fetch a page (returns raw HTML string or None)
        base_url: Base URL for the vendor
        config: Pagination configuration
        verbose: Print progress messages
        
    Returns:
        List of unique reference URLs found across all pages
    """
    all_links: Set[str] = set()
    page_num = 0
    consecutive_empty = 0
    
    if verbose:
        print(f"Starting pagination with strategy: {strategy.__class__.__name__}")
    
    while True:
        # Build URL for this page
        page_url = strategy.build_url(base_url, page_num, config.page_size)
        
        if verbose:
            print(f"  Fetching page {page_num + 1} ({page_url[:80]}...)", flush=True)
        
        # Fetch page content
        html_content = page_fetcher(page_url)
        
        if html_content is None:
            consecutive_empty += 1
            if verbose:
                print(f"    ✗ Could not fetch/parse page ({consecutive_empty}/{config.max_consecutive_empty} consecutive failed)")
                print(f"       URL: {page_url}")
            
            if consecutive_empty >= config.max_consecutive_empty:
                if verbose:
                    print(f"    Reached {config.max_consecutive_empty} consecutive failed pages, stopping")
                break
            page_num += 1
            continue
        
        # Extract links from page
        page_links = link_extractor(html_content, base_url)
        
        # Check for duplicates BEFORE adding to all_links
        new_links = page_links - all_links
        new_urls_count = len(new_links)
        duplicates_count = len(page_links) - new_urls_count
        
        if verbose:
            print(f"    ✓ Found {len(page_links)} links on this page ({new_urls_count} new, {duplicates_count} duplicates)", flush=True)
            print(f"    📊 Total unique URLs so far: {len(all_links)}", flush=True)
        
        # Check if we should stop (using state BEFORE adding page_links to all_links)
        should_stop, reason = strategy.should_stop(
            page_links, all_links, page_num, consecutive_empty, config, html_content
        )
        
        if should_stop:
            if verbose:
                print(f"    ⚠ {reason}")
                print(f"    Stopping pagination (found {len(all_links)} total unique URLs)")
            break
        
        # Now add the new links to all_links
        all_links.update(page_links)
        
        # Update consecutive empty counter
        if len(page_links) == 0:
            consecutive_empty += 1
            if verbose:
                print(f"    No links found ({consecutive_empty}/{config.max_consecutive_empty} consecutive empty)")
        else:
            consecutive_empty = 0
        
        page_num += 1
    
    result = sorted(list(all_links))
    if verbose:
        print(f"\n✓ Found {len(result)} total unique URLs across {page_num} pages", flush=True)
    
    return result

