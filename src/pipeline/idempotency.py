"""Idempotency checks for all pipeline phases."""

import os
import json
import glob
from typing import Set, List, Dict
from pathlib import Path

from graph.neo4j_client import Neo4jClient


def get_existing_urls(vendor_name: str, db: Neo4jClient) -> Set[str]:
    """
    Get set of URLs that already exist in Neo4j for a vendor.
    
    Phase 1 check: Query Neo4j for existing Reference URLs.
    
    Args:
        vendor_name: Vendor name (e.g., 'MongoDB', 'Snowflake')
        db: Neo4jClient instance
        
    Returns:
        Set of existing URLs
    """
    with db.driver.session() as session:
        result = session.run("""
            MATCH (v:Vendor {name: $vendor_name})-[:PUBLISHED]->(r:Reference)
            RETURN r.url as url
        """, {'vendor_name': vendor_name})
        
        urls = {record['url'] for record in result}
        return urls


def filter_new_urls(vendor_name: str, discovered_urls: List[str], db: Neo4jClient) -> List[str]:
    """
    Filter discovered URLs to only include new ones (not in Neo4j).
    
    Phase 1 check: Compare discovered URLs with existing URLs.
    
    Args:
        vendor_name: Vendor name
        discovered_urls: List of discovered URLs
        db: Neo4jClient instance
        
    Returns:
        List of new URLs (not in database)
    """
    existing_urls = get_existing_urls(vendor_name, db)
    new_urls = [url for url in discovered_urls if url not in existing_urls]
    return new_urls


def get_scraped_urls(vendor_name: str) -> Set[str]:
    """
    Get set of URLs that have already been scraped (files exist).
    
    Phase 2 check: Check filesystem for scraped files.
    
    Args:
        vendor_name: Vendor name (lowercase, e.g., 'mongodb')
        
    Returns:
        Set of URLs that have scraped files
    """
    vendor_dir = Path('data') / 'scraped' / vendor_name.lower()
    
    if not vendor_dir.exists():
        return set()
    
    # Find all JSON files (exclude discovered_urls files)
    ref_files = glob.glob(str(vendor_dir / '*.json'))
    ref_files = [f for f in ref_files if 'discovered_urls' not in f]
    
    scraped_urls = set()
    for filepath in ref_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'url' in data:
                    scraped_urls.add(data['url'])
        except Exception:
            # Skip files that can't be read
            continue
    
    return scraped_urls


def filter_unscraped_urls(vendor_name: str, urls: List[str]) -> List[str]:
    """
    Filter URLs to only include ones that haven't been scraped yet.
    
    Phase 2 check: Compare URLs with existing scraped files.
    
    Args:
        vendor_name: Vendor name (lowercase)
        urls: List of URLs to check
        
    Returns:
        List of URLs that don't have scraped files
    """
    scraped_urls = get_scraped_urls(vendor_name)
    unscraped_urls = [url for url in urls if url not in scraped_urls]
    return unscraped_urls


def get_unclassified_references(vendor_name: str, db: Neo4jClient, limit: int = 1000) -> List[Dict]:
    """
    Get references that need classification (classified=false).
    
    Phase 4 check: Query Neo4j for unclassified references.
    
    Args:
        vendor_name: Vendor name
        db: Neo4jClient instance
        limit: Maximum number of references to return
        
    Returns:
        List of reference dicts with id, url, text
    """
    with db.driver.session() as session:
        result = session.run("""
            MATCH (v:Vendor {name: $vendor_name})-[:PUBLISHED]->(r:Reference)
            WHERE r.classified = false OR r.classified IS NULL
            RETURN r.id as id, r.url as url, r.raw_text as text
            LIMIT $limit
        """, {'vendor_name': vendor_name, 'limit': limit})
        
        references = [
            {
                'id': record['id'],
                'url': record['url'],
                'text': record['text']
            }
            for record in result
        ]
        
        return references


def count_existing_references(vendor_name: str, db: Neo4jClient) -> int:
    """
    Count total references for a vendor in Neo4j.
    
    Args:
        vendor_name: Vendor name
        db: Neo4jClient instance
        
    Returns:
        Count of references
    """
    with db.driver.session() as session:
        result = session.run("""
            MATCH (v:Vendor {name: $vendor_name})-[:PUBLISHED]->(r:Reference)
            RETURN count(r) as count
        """, {'vendor_name': vendor_name})
        
        record = result.single()
        return record['count'] if record else 0


def count_classified_references(vendor_name: str, db: Neo4jClient) -> int:
    """
    Count classified references for a vendor.
    
    Args:
        vendor_name: Vendor name
        db: Neo4jClient instance
        
    Returns:
        Count of classified references
    """
    with db.driver.session() as session:
        result = session.run("""
            MATCH (v:Vendor {name: $vendor_name})-[:PUBLISHED]->(r:Reference)
            WHERE r.classified = true
            RETURN count(r) as count
        """, {'vendor_name': vendor_name})
        
        record = result.single()
        return record['count'] if record else 0

