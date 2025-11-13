# Quick Start: Adding a New Vendor

## The Simple Process

**Just 2 steps:**

1. **Add vendor config** → `data/vendors.json`
2. **Run pipeline** → `python scripts/run_pipeline.py --vendors newvendor`

**Done!** The pipeline handles everything automatically.

---

## Step 1: Add Vendor Config

Edit `data/vendors.json`:

```json
{
  "newvendor": {
    "name": "New Vendor",
    "website": "https://newvendor.com",
    "discovery_method": "sitemap",
    "scraper_class": "UniversalScraper",
    "enabled": true,
    "scraper": {
      "link_patterns": ["/customers/"],
      "exclude_patterns": ["/customers/"]
    }
  }
}
```

**If using sitemap**, also add to `src/utils/sitemap_discovery.py` → `VENDOR_CONFIGS`.

**If using pagination**, add `pagination` section to scraper config.

---

## Step 2: Run Pipeline

```bash
# Single vendor
python scripts/run_pipeline.py --vendors newvendor

# Multiple vendors
python scripts/run_pipeline.py --vendors vendor1,vendor2,vendor3

# All enabled vendors
python scripts/run_pipeline.py

# Specific phases only
python scripts/run_pipeline.py --vendors newvendor --phases 1,2

# Dry run (test without executing)
python scripts/run_pipeline.py --vendors newvendor --dry-run
```

---

## What Happens Automatically

✅ **Phase 1**: URL Discovery (sitemap or pagination)  
✅ **Phase 2**: Content Scraping (Scrapy first, HyperBrowser fallback)  
✅ **Phase 3**: Database Loading (with deduplication)  
✅ **Phase 4**: Classification (only unclassified references)

All phases are **idempotent** - safe to re-run!

---

## Need Help?

- **Detailed guide**: See [docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)
- **Configuration examples**: See `data/vendors.json` for existing vendors
- **Troubleshooting**: See README.md Troubleshooting section

---

## Daily Workflow

```bash
# Run all vendors (only processes new content)
python scripts/run_pipeline.py

# Estimated cost: $0-5 per day (only new content)
```

