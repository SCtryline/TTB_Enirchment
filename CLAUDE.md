# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TTB COLA Registry Management System — an enterprise data management platform for the alcohol beverage import industry. It processes TTB (Alcohol and Tobacco Tax and Trade Bureau) COLA registry CSV files, matches brands to importers via permit numbers, provides AI-powered brand enrichment and consolidation, and integrates with Apollo.io for contact discovery. Built for Helmsman Imports to identify and target competitor brands (MHW/Parkstreet portfolios).

## Commands

### Running the Application
```bash
pip install -r requirements.txt
python app.py
# Starts Flask dev server on http://localhost:5000
```

### Running Tests
```bash
python -m pytest tests/
python -m pytest tests/test_production_integration.py   # single test file
```

Tests are in `tests/` — they are integration-style tests, not unit tests. No pytest config file exists.

### Environment Variables (in .env file, loaded via python-dotenv)
- `APOLLO_API_KEY` — Apollo.io API key for contact enrichment
- `TWOCAPTCHA_API_KEY` — 2Captcha API key for CAPTCHA solving during web scraping

## Architecture

### Entry Point
`app.py` — monolithic Flask app (~3600 lines) containing all routes, API endpoints, caching logic, and the cache invalidation system. This is the central orchestrator that wires everything together. Includes URL research export/import endpoints near the end of file.

### Core Modules (`core/`)
- `database.py` (94KB) — `BrandDatabaseV2` class wrapping SQLite with WAL mode. All database access goes through this. Tables: `brands`, `skus`, `master_importers`, `consolidation_history`. Uses JSON fields for complex data (enrichment_data, apollo_data).
- `config.py` — centralized configuration (DB paths, web config, enrichment settings)
- `market_insights.py` — analytics engine with 10+ analytical modules for market intelligence
- `pdf_generator.py` — PDF report generation for executive exports

### Enrichment System (`enrichment/`)
AI-powered brand website discovery with multiple search backends:
- `orchestrator.py` (83KB) — main orchestration, routes to appropriate search strategy
- `search_engine.py` — production browser-based search with anti-detection (Playwright)
- `safe_search.py` — HTTP-based search (no browser needed)
- `fast_search.py` — lightweight dev-mode search
- `learning_system.py` — agentic learning agent that improves search accuracy from feedback
- `ranking_system.py` — 5-tier strategic prioritization. Tier 1 = competitor brands (MHW/Parkstreet auto-detected). Scoring: competitor status (40pts), importer links (20pts), website presence (15pts), product type hierarchy (spirits > wine > beer)
- `apollo_enrichment.py` — Apollo.io contact enrichment with 3-track system (auto/manual/direct entry) and credit-controlled contact selection
- `url_scorer.py` — URL quality scoring for search results
- Anti-detection stack: `stealth_system.py`, `captcha_handler.py`, `captcha_solver.py`, `human_behavior.py`, `proxy_manager.py`

### Brand Consolidation (`brand_consolidation/`)
Detects and merges duplicate/related brands:
- `core.py` (61KB) — consolidation orchestrator, similarity matching, proposal generation
- `sku_brand_analyzer.py` — distinguishes SKUs from parent brands via URL/domain analysis
- `brand_matcher.py` — name similarity and variation detection
- `agentic_consolidator.py` — self-improving consolidation via user feedback
- `config.py` — consolidation rules and thresholds

### Frontend (`web/`)
Server-rendered Jinja2 templates with vanilla JavaScript:
- `templates/` — 16 HTML templates. Key pages: `brands.html`, `brand_detail.html`, `audit.html`, `dashboard.html`, `enrichment_rankings.html`, `data.html`, `importers.html`
- `static/js/cache_buster.js` — polls `/api/database_version` every 5 seconds, auto-refreshes UI on data changes
- Each page has its own CSS and JS file (e.g., `brands.js`, `brands.css`)

**UI Foundation (Phase 1 SaaS Redesign):**
- `static/css/base.css` — loaded FIRST on every page. Contains `:root` variables (canonical + backward-compatible aliases for audit/producers/consolidation/enrichment naming), CSS reset, body styles, `.app-layout` flex container, `.main-content-area` with sidebar offset, sidebar nav styles, mobile responsive, utility classes.
- `templates/includes/sidebar.html` — self-contained dark sidebar nav (`#0f172a`) with inline SVGs. Sections: Main (Home, Dashboard, Data), Registry (Brands, Importers, Producers), Intelligence (Rankings, Audit, Learning). Active state via `request.endpoint`. Mobile hamburger toggle. No external dependencies.
- `templates/includes/icons.html` — Jinja2 macro `icon(name, size, class)` with 47 Lucide SVG icons. Usage: `{% from 'includes/icons.html' import icon %}` then `{{ icon('search', 16) }}`.
- **Page CSS load order**: `base.css` first, then page-specific CSS (e.g., `brands.css`). Page CSS wins by cascade for same-specificity rules.
- **Template structure**: All pages wrap content in `<div class="app-layout">{% include 'includes/sidebar.html' %}<div class="main-content-area">...content...</div></div>`.
- **No emoji in templates** — all replaced with Lucide SVG icon macro calls.

### Data Storage (`data/`)
- `database/brands.db` — primary SQLite database
- `consolidation_learning/` — AI consolidation pattern data
- JSON caches: `production_search_cache.json`, `safe_search_cache.json`, `enrichment_results.json`

## Key Data Flow

1. **CSV Upload** (`/data`) → parse TTB COLA/importer CSVs → extract brands/SKUs → match to importers via permit numbers → store in SQLite
2. **Ranking** → score all brands by business value (competitor detection, product type, data completeness) → assign to 5 tiers
3. **Enrichment** → search for brand websites using selected search backend → learning system records patterns → update database
4. **Apollo Integration** → use discovered domains for contact lookup → user selects contacts → unlock emails (1 credit each) → save to DB
5. **Consolidation** → detect duplicate/related brands via name similarity + URL analysis → generate proposals → user reviews in audit UI → merge
6. **URL Research** (`/data`) → export filtered brands needing URLs as CSV/Excel (`/export_brands_needing_urls`) → assistant researches and fills in URLs → re-upload via `/upload_brand_urls` → `bulk_update_brand_urls()` writes to `enrichment_data` with `source: "manual_import"`
7. **Cache Invalidation** → any DB write increments `db_version` → clears all server caches → client detects version change → auto-refresh

## Key Patterns

- **Cache invalidation**: `invalidate_all_caches()` in `app.py` must be called after every database write. It increments `db_version` and clears all 4 caches (filter, brand_list, all_brands, stats).
- **Enrichment data structure**: Flat JSON stored in `enrichment_data` column — fields: `url`, `domain`, `confidence`, `source`, `verification_status`, `notes`, `updated_date`, `title`, `description`. Queried via `json_extract(enrichment_data, '$.url')`. Bulk URL imports set `source: "manual_import"` and `verification_status: "unverified"`.
- **Frontend visibility**: Use `classList.add/remove('hidden')` for show/hide. Use `safeJsonParse(response)` for JSON parsing.
- **Domain handling**: Auto-strips `www.` prefix during processing.
- **Database concurrency**: SQLite WAL mode enabled. All access through `BrandDatabaseV2`.
- **CSS variable aliases**: `base.css` defines canonical variables (`--primary-color`, `--gray-200`, etc.) plus aliases for backward compatibility: `--primary-blue` (audit/producers), `--surface-color`/`--border-color`/`--card-bg` (consolidation/enrichment), `--success`/`--warning`/`--error` (producers). New CSS should use the canonical names from `:root` in `base.css`.
- **Adding new icons**: Add a new `{%- elif name == 'icon-name' -%}` block in `icons.html` before the `{%- else -%}` fallback. Use Lucide icon SVG paths. Unknown icon names render as a plain circle fallback.

## Critical Data (back up before modifying)
- `data/database/brands.db`
- `data/consolidation_learning/`
- Any `*_cache.json` files in `data/`
