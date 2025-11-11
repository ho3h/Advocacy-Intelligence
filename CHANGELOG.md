# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-11

### Added
- URL deduplication: Neo4j client now checks if a URL already exists before creating a new reference
- URL filtering: Scraper now filters out invalid URLs (listing pages, URLs without company names)
- Quality filtering: Scraper skips low-quality scrapes (<100 words)
- Cleanup script (`scripts/cleanup_duplicates.py`) to remove duplicate references and bad URLs
- Improved classification prompts with better guidance for extracting company size and region

### Changed
- `load_raw_reference()` now returns `None` if URL already exists (instead of creating duplicates)
- Scraper URL extraction logic improved to validate case-study and video URLs have company names
- Classification prompts enhanced with explicit extraction guidelines for company size and region
- Pipeline script now reports skipped duplicates

### Fixed
- Fixed duplicate reference creation issue (same URL stored multiple times)
- Fixed bad URLs being stored (listing pages like `/all-customers/` without `/case-study/` or `/video/`)
- Improved company size and region extraction accuracy in classification

## [0.1.0] - 2025-01-10

### Added
- Initial project setup
- Snowflake scraper with HyperBrowser.ai fallback
- Neo4j graph database integration
- Google Gemini classification system
- Basic pipeline script (`scripts/test_pipeline.py`)
- Taxonomy files for industries, use cases, and company sizes
- Project documentation and agent instructions

### Features
- Scrapes customer references from Snowflake website
- Stores raw scraped data in Neo4j
- Classifies references using LLM (Gemini)
- Extracts structured data: customers, industries, use cases, outcomes, technologies, personas
- Graph relationships: Vendor → Reference → Customer → Industry, Use Cases, Outcomes, etc.

[0.2.0]: https://github.com/yourusername/Advocacy-Intelligence/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/Advocacy-Intelligence/releases/tag/v0.1.0

