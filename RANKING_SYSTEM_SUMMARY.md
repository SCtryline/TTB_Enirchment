# Enrichment Ranking System - Complete Implementation

## Overview
The enrichment ranking system prioritizes brands for Apollo API and manual enrichment based on business value and enrichment likelihood.

## Scoring Factors (Max 100 Points)

### 1. **Strategic Partners** (40 points)
- Parkstreet or MHW owned brands get highest priority
- Automatically qualifies for Tier 1/2

### 2. **Importer Relationship** (20 points)
- Any brand with an importer relationship
- Critical for distribution and market presence

### 3. **Website/URL Presence** (15 points) ✨ NEW
- Brands with existing URLs are Apollo-ready
- Significantly improves enrichment success rate
- Apollo can find contacts using domain information

### 4. **Product Type** (35 points max)
Priority order matching business focus:

**Spirits (25-35 points):**
- Ultra Premium (35): Single Malt Scotch, Cognac, Mezcal
- Premium (32): Straight Bourbon/Rye, Tequila
- Core (30): Vodka, Rum, Gin, Bourbon, Rye
- Standard (28): Other spirits varieties
- Liqueurs (25): Coffee, Fruit liqueurs

**Wine (12-20 points):**
- Premium (20): Champagne, Sparkling
- Fortified (18): Port, Sherry, Dessert
- Table (15): Red, White, Rose
- Specialty (12): Honey-based, Cider

**Beer (8-10 points):**
- Craft (10): Stouts, Porters, IPAs, Specialties
- Standard (8): Ales, Lagers, Pilsners

### 5. **Business Metrics** (15 points max)
- High SKU count (5+ SKUs): 10 points
- Medium SKU count (2-4 SKUs): 7 points
- Single SKU: 3 points
- Recent activity (last 180 days): 5 points

### 6. **Market Presence** (10 points max)
- Multiple countries: 5 points
- Multiple permits: 3 points
- Premium segment: 2 points

## Tier Classification

| Tier | Score | Description | Action |
|------|-------|-------------|--------|
| **1** | 90-100 | Critical Priority | Auto-enrichment queue |
| **2** | 70-89 | High Priority | Batch processing |
| **3** | 50-69 | Standard Priority | Manual review |
| **4** | 30-49 | Low Priority | On request only |
| **5** | <30 | Manual Only | Inactive/test brands |

## Current Database Statistics (Sept 2025)

- **Total Brands**: 21,604
- **Brands with Websites**: 202 (Apollo-ready)
- **Already Enriched**: 202 brands
- **Spirits Brands**: 2,673
- **Wine Brands**: 13,684
- **Beer Brands**: 4,262
- **Brands with Importers**: 11,866

### Tier Distribution:
- **Tier 1**: 0 brands (no Parkstreet/MHW identified yet)
- **Tier 2**: 180 brands (107 already enriched)
- **Tier 3**: 3,974 brands (84 enriched)
- **Tier 4**: 10,277 brands (11 enriched)
- **Tier 5**: 7,173 brands (inactive/low priority)

## Key Features

### Web Interface (`/enrichment_rankings`)
- Real-time ranking display
- Tier-based filtering
- Score breakdown for each brand
- One-click enrichment
- Apollo-ready indicator

### API Endpoints
- `GET /api/enrichment/rankings` - All rankings with filters
- `GET /api/enrichment/ranking/{brand_name}` - Individual brand score
- `GET /api/enrichment/ranking_stats` - System statistics
- `GET /api/enrichment/priority_queue` - Queue by tier

### Batch Processing
```bash
# Process Tier 1 brands
python -m enrichment.batch_enrichment --tier 1

# Process top 10 brands from Tier 2
python -m enrichment.batch_enrichment --tier 2 --limit 10

# Check queue status
python -m enrichment.batch_enrichment --status

# Use Apollo API (when configured)
python -m enrichment.batch_enrichment --tier 1 --apollo
```

## Apollo Integration Benefits

Brands with URLs (202 currently) are perfect for Apollo because:
1. **Domain-based search** - Apollo can find company info from domain
2. **Contact discovery** - Find decision makers at the company
3. **Verified data** - Higher quality than web scraping
4. **Bulk enrichment** - Process multiple brands efficiently

## Priority Examples

### Example 1: Highest Priority (95+ points)
- Parkstreet-owned (40) + Has URL (15) + Premium Spirits (35) + 5 SKUs (10) = 100 points
- **Action**: Immediate Apollo enrichment

### Example 2: High Priority (70-89 points)
- Has Importer (20) + Has URL (15) + Spirits (30) + 3 SKUs (7) = 72 points
- **Action**: Batch Apollo enrichment

### Example 3: Standard Priority (50-69 points)
- Has Importer (20) + Wine (15) + Multiple Countries (5) + 2 SKUs (7) + Recent (5) = 52 points
- **Action**: Manual enrichment queue

### Example 4: Low Priority (30-49 points)
- No Importer (0) + Spirits (30) + Single SKU (3) = 33 points
- **Action**: Only on specific request

## Implementation Files

- `enrichment/ranking_system.py` - Core ranking algorithm
- `enrichment/batch_enrichment.py` - Batch processing engine
- `web/templates/enrichment_rankings.html` - Web interface
- `app.py` - API endpoints (lines 2544-2685)

## Next Steps

1. **Connect Apollo API** - Add API key to environment
2. **Identify Strategic Partners** - Mark Parkstreet/MHW brands in database
3. **Run Tier 2 Batch** - 73 unenriched high-priority brands ready
4. **Monitor Success Rate** - Track Apollo vs manual enrichment

---
*System ready for Apollo integration with 202 URL-enabled brands prioritized*