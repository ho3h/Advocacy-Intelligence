"""Unified pipeline system for processing multiple vendors through all phases."""

from .vendor_config import load_vendor_configs, get_vendor_config
from .scraper_registry import get_scraper
from .idempotency import (
    get_existing_urls,
    filter_new_urls,
    get_scraped_urls,
    filter_unscraped_urls,
    get_unclassified_references
)
from .runner import PipelineRunner
from .reporting import PipelineReporter

__all__ = [
    'load_vendor_configs',
    'get_vendor_config',
    'get_scraper',
    'get_existing_urls',
    'filter_new_urls',
    'get_scraped_urls',
    'filter_unscraped_urls',
    'get_unclassified_references',
    'PipelineRunner',
    'PipelineReporter',
]

