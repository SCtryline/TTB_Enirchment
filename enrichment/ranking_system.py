"""
Enrichment Ranking System
Prioritizes brands for enrichment based on business priorities:
1. Parkstreet/MHW ownership (highest priority)
2. Importer relationships
3. Product type (Spirits > Wine > Beer)
4. Business metrics (SKUs, activity)
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class EnrichmentRankingSystem:
    """Calculates enrichment priority scores for brands"""

    def __init__(self, db_path: str = 'data/brands.db'):
        self.db_path = db_path

        # Competitor targets (MHW/Parkstreet brands to poach)
        # These brands are HIGH PRIORITY - imported by competitors we want to steal from
        self.COMPETITOR_TARGETS = {
            'PARKSTREET': ['PARKSTREET', 'PARK STREET', 'PARK-STREET'],
            'MHW': ['MHW', 'M.H.W', 'MHW LTD', 'MHW LIMITED']
        }

        # Spirits categories with scores
        self.SPIRITS_CATEGORIES = {
            # Ultra Premium (35 points)
            'SINGLE MALT SCOTCH WHISKY': 35,
            'COGNAC': 35,
            'MEZCAL FB': 35,
            'MEZCAL': 35,

            # Premium (32 points)
            'STRAIGHT BOURBON WHISKY': 32,
            'STRAIGHT RYE WHISKY': 32,
            'TEQUILA FB': 32,
            'TEQUILA': 32,

            # Core Spirits (30 points)
            'BOURBON WHISKY': 30,
            'RYE WHISKY': 30,
            'VODKA': 30,
            'VODKA SPECIALTIES': 30,
            'RUM': 30,
            'RUM SPECIALTIES': 30,
            'GIN': 30,
            'OTHER GIN': 30,

            # Standard Spirits (28 points)
            'OTHER RUM (WHITE)': 28,
            'OTHER RUM': 28,
            'OTHER WHISKY BIB': 28,
            'WHISKY SPECIALTIES': 28,
            'OTHER STRAIGHT WHISKY': 28,
            'WHISKY': 28,
            'SCOTCH WHISKY': 28,

            # Specialty/Liqueurs (25 points)
            'COFFEE (CAFE) LIQUEUR': 25,
            'COFFEE LIQUEUR': 25,
            'OTHER FRUITS & PEELS LIQUEURS': 25,
            'LIQUEUR': 25,
            'LIQUEURS': 25,
            'STRAIGHT BOURBON WHISKY BLENDS': 25,
            'STRAIGHT RYE WHISKY BLENDS': 25,
            'WHISKY BLENDS': 25,
            'BRANDY': 25,
            'ARMAGNAC': 25
        }

        # Wine categories with scores
        self.WINE_CATEGORIES = {
            # Premium Wine (20 points)
            'SPARKLING WINE/CHAMPAGNE': 20,
            'CHAMPAGNE': 20,
            'SPARKLING WINE': 20,
            '84': 20,  # Sparkling wine code

            # Fortified Wine (18 points)
            'DESSERT /PORT/SHERRY/(COOKING) WINE': 18,
            'PORT': 18,
            'SHERRY': 18,
            'DESSERT WINE': 18,
            '88': 18,  # Dessert wine code

            # Table Wine (15 points)
            'TABLE RED WINE': 15,
            'TABLE WHITE WINE': 15,
            'ROSE WINE': 15,
            'RED WINE': 15,
            'WHITE WINE': 15,
            '80': 15,  # Red wine code
            '81': 15,  # White wine code
            '80A': 15,  # Rose wine code

            # Specialty Wine (12 points)
            'HONEY BASED TABLE WINE': 12,
            'APPLE TABLE WINE/CIDER': 12,
            'FRUIT WINE': 12,
            '82M': 12,  # Honey wine code
            '83C': 12,  # Cider code
        }

        # Beer categories with scores
        self.BEER_CATEGORIES = {
            # Craft/Specialty (10 points)
            'MALT BEVERAGES SPECIALITIES - FLAVORED': 10,
            'MALT BEVERAGES SPECIALTIES': 10,
            'STOUT': 10,
            'PORTER': 10,
            'IPA': 10,
            '906': 10,  # Malt beverages code
            '904': 10,  # Stout code
            '900': 10,  # Porter code

            # Standard Beer (8 points)
            'ALE': 8,
            'BEER': 8,
            'LAGER': 8,
            'PILSNER': 8,
            '902': 8,  # Ale code
            '901': 8,  # Beer code
        }

    def _get_connection(self) -> sqlite3.Connection:
        """Create database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _is_competitor_target(self, brand_data: Dict) -> bool:
        """Check if brand is imported by MHW or Parkstreet (competitors to poach from)"""
        # Check importers
        if brand_data.get('importers'):
            importers = json.loads(brand_data['importers']) if isinstance(brand_data['importers'], str) else brand_data['importers']
            for permit, importer_info in importers.items():
                if isinstance(importer_info, dict):
                    # Check both owner_name and operating_name (many operating_name are 'nan')
                    owner_name = importer_info.get('owner_name', '').upper()
                    operating_name = importer_info.get('operating_name', '').upper()
                    # Also check legacy 'name' field for backward compatibility
                    legacy_name = importer_info.get('name', '').upper()

                    # Check all name fields against competitor targets
                    names_to_check = [owner_name, operating_name, legacy_name]
                    for name in names_to_check:
                        if name and name != 'NAN':  # Skip empty and 'nan' values
                            for competitor, variants in self.COMPETITOR_TARGETS.items():
                                if any(variant in name for variant in variants):
                                    logger.info(f"🎯 Poaching target detected: {name} (competitor: {competitor})")
                                    return True

        # Check producers
        if brand_data.get('producers'):
            producers = json.loads(brand_data['producers']) if isinstance(brand_data['producers'], str) else brand_data['producers']
            for permit, producer_info in producers.items():
                if isinstance(producer_info, dict):
                    # Check both owner_name and operating_name for producers too
                    owner_name = producer_info.get('owner_name', '').upper()
                    operating_name = producer_info.get('operating_name', '').upper()
                    legacy_name = producer_info.get('name', '').upper()

                    names_to_check = [owner_name, operating_name, legacy_name]
                    for name in names_to_check:
                        if name and name != 'NAN':
                            for competitor, variants in self.COMPETITOR_TARGETS.items():
                                if any(variant in name for variant in variants):
                                    logger.info(f"🎯 Poaching target detected: {name} (competitor: {competitor})")
                                    return True

        return False

    def _has_importer(self, brand_data: Dict) -> bool:
        """Check if brand has any importer"""
        if not brand_data.get('importers'):
            return False

        importers = json.loads(brand_data['importers']) if isinstance(brand_data['importers'], str) else brand_data['importers']
        return bool(importers) and len(importers) > 0

    def _get_product_score(self, brand_data: Dict) -> int:
        """Calculate score based on product type"""
        max_score = 0

        if not brand_data.get('class_types'):
            return 0

        class_types = json.loads(brand_data['class_types']) if isinstance(brand_data['class_types'], str) else brand_data['class_types']

        for class_type in class_types:
            if not class_type:
                continue

            class_type_upper = str(class_type).upper().strip()

            # Check spirits
            for spirit_type, score in self.SPIRITS_CATEGORIES.items():
                if spirit_type in class_type_upper or class_type_upper == spirit_type:
                    max_score = max(max_score, score)

            # Check wine
            for wine_type, score in self.WINE_CATEGORIES.items():
                if wine_type in class_type_upper or class_type_upper == wine_type:
                    max_score = max(max_score, score)

            # Check beer
            for beer_type, score in self.BEER_CATEGORIES.items():
                if beer_type in class_type_upper or class_type_upper == beer_type:
                    max_score = max(max_score, score)

        return max_score

    def _get_sku_count_score(self, sku_count: int) -> int:
        """Calculate score based on SKU count"""
        if sku_count >= 5:
            return 10
        elif sku_count >= 2:
            return 7
        elif sku_count == 1:
            return 3
        return 0

    def _has_recent_activity(self, brand_data: Dict, days: int = 180) -> bool:
        """Check if brand has recent activity"""
        # Check created_date
        if brand_data.get('created_date'):
            try:
                created = datetime.fromisoformat(brand_data['created_date'].replace('Z', '+00:00'))
                if (datetime.now() - created).days <= days:
                    return True
            except:
                pass

        # Check updated_at
        if brand_data.get('updated_at'):
            try:
                updated = datetime.fromisoformat(brand_data['updated_at'].replace('Z', '+00:00'))
                if (datetime.now() - updated).days <= days:
                    return True
            except:
                pass

        return False

    def _has_multiple_countries(self, brand_data: Dict) -> bool:
        """Check if brand has multiple countries"""
        if not brand_data.get('countries'):
            return False

        countries = json.loads(brand_data['countries']) if isinstance(brand_data['countries'], str) else brand_data['countries']
        return len(set(countries)) > 1

    def _has_multiple_permits(self, brand_data: Dict) -> bool:
        """Check if brand has multiple permit types"""
        permits = []

        if brand_data.get('permit_numbers'):
            permit_list = json.loads(brand_data['permit_numbers']) if isinstance(brand_data['permit_numbers'], str) else brand_data['permit_numbers']
            permits.extend(permit_list)

        if brand_data.get('brand_permits'):
            brand_permit_list = json.loads(brand_data['brand_permits']) if isinstance(brand_data['brand_permits'], str) else brand_data['brand_permits']
            permits.extend(brand_permit_list)

        # Check for different permit types (I = importer, DSP = distillery, BR = brewery, BWN = winery)
        permit_types = set()
        for permit in permits:
            if '-I-' in permit:
                permit_types.add('importer')
            elif 'DSP' in permit:
                permit_types.add('distillery')
            elif 'BR-' in permit:
                permit_types.add('brewery')
            elif 'BWN' in permit:
                permit_types.add('winery')

        return len(permit_types) > 1

    def _is_premium_segment(self, brand_data: Dict) -> bool:
        """Check if brand is in premium segment"""
        if not brand_data.get('class_types'):
            return False

        class_types = json.loads(brand_data['class_types']) if isinstance(brand_data['class_types'], str) else brand_data['class_types']

        premium_indicators = [
            'SINGLE MALT', 'COGNAC', 'MEZCAL', 'CHAMPAGNE',
            'STRAIGHT BOURBON', 'STRAIGHT RYE', 'XO', 'VSOP',
            'RESERVE', 'ESTATE', 'GRAND CRU', 'PREMIER CRU'
        ]

        for class_type in class_types:
            if any(indicator in str(class_type).upper() for indicator in premium_indicators):
                return True

        return False

    def _has_website(self, brand_data: Dict) -> bool:
        """Check if brand has a website/URL for Apollo enrichment"""
        # Check enrichment_data for URL
        if brand_data.get('enrichment_data'):
            try:
                enrichment = json.loads(brand_data['enrichment_data']) if isinstance(brand_data['enrichment_data'], str) else brand_data['enrichment_data']

                # Check flat structure
                if enrichment.get('url'):
                    return True

                # Check nested structure (legacy)
                if enrichment.get('website') and isinstance(enrichment['website'], dict):
                    if enrichment['website'].get('url'):
                        return True
            except:
                pass

        # Check legacy website field
        if brand_data.get('website'):
            return True

        return False

    def calculate_score(self, brand_data: Dict) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate enrichment priority score for a brand

        Returns:
            Tuple of (score, breakdown) where breakdown shows component scores
        """
        score = 0
        breakdown = {
            'competitor_target': 0,  # MHW/Parkstreet brands to poach
            'importer': 0,
            'has_website': 0,  # Website presence for Apollo
            'product_type': 0,
            'sku_volume': 0,
            'recent_activity': 0,
            'multiple_countries': 0,
            'multiple_permits': 0,
            'premium_segment': 0,
            'total': 0
        }

        # 1. Competitor Target Check (40 points max) - MHW/Parkstreet brands to poach
        if self._is_competitor_target(brand_data):
            score += 40
            breakdown['competitor_target'] = 40
        elif self._has_importer(brand_data):
            score += 20
            breakdown['importer'] = 20

        # 2. Website/URL Presence (15 points) - IMPORTANT FOR APOLLO
        # Brands with URLs get significant boost as Apollo can enrich them
        if self._has_website(brand_data):
            score += 15
            breakdown['has_website'] = 15

        # 3. Product Type Score (35 points max)
        product_score = self._get_product_score(brand_data)
        score += product_score
        breakdown['product_type'] = product_score

        # 4. SKU Volume Score (10 points max)
        sku_count = brand_data.get('sku_count', 0)
        sku_score = self._get_sku_count_score(sku_count)
        score += sku_score
        breakdown['sku_volume'] = sku_score

        # 5. Recent Activity (5 points)
        if self._has_recent_activity(brand_data):
            score += 5
            breakdown['recent_activity'] = 5

        # 6. Market Presence (10 points max)
        if self._has_multiple_countries(brand_data):
            score += 5
            breakdown['multiple_countries'] = 5

        if self._has_multiple_permits(brand_data):
            score += 3
            breakdown['multiple_permits'] = 3

        if self._is_premium_segment(brand_data):
            score += 2
            breakdown['premium_segment'] = 2

        # Cap at 100
        total_score = min(score, 100)
        breakdown['total'] = total_score

        return total_score, breakdown

    def get_tier(self, score: int, is_competitor_target: bool = False) -> Tuple[int, str]:
        """Get tier based on score

        Args:
            score: Calculated priority score
            is_competitor_target: If True, automatically assign Tier 1 (poaching targets)
        """
        # CRITICAL: All MHW/Parkstreet brands are Tier 1 (poaching opportunities)
        if is_competitor_target:
            return 1, "Tier 1 - Poaching Target (MHW/Parkstreet)"

        # Normal tier assignment for non-competitor brands
        if score >= 90:
            return 1, "Critical Priority - Auto Enrichment"
        elif score >= 70:
            return 2, "High Priority - Batch Processing"
        elif score >= 50:
            return 3, "Standard Priority - Manual Review"
        elif score >= 30:
            return 4, "Low Priority - On Request"
        else:
            return 5, "Manual Only - Inactive/Test"

    def rank_all_brands(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Calculate rankings for all brands in database

        Returns:
            List of brands with scores, sorted by priority
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get all brands with SKU counts
        query = """
        SELECT
            b.*,
            COUNT(s.ttb_id) as sku_count
        FROM brands b
        LEFT JOIN skus s ON b.brand_name = s.brand_name
        GROUP BY b.brand_name
        """

        cursor.execute(query)
        brands = cursor.fetchall()

        ranked_brands = []
        for brand_row in brands:
            # Convert Row to dict
            brand_data = dict(brand_row)

            # Calculate score
            score, breakdown = self.calculate_score(brand_data)

            # Check if this is a competitor target (MHW/Parkstreet brand to poach)
            is_competitor = self._is_competitor_target(brand_data)
            tier, tier_description = self.get_tier(score, is_competitor_target=is_competitor)

            # Add to results
            ranked_brands.append({
                'brand_name': brand_data['brand_name'],
                'score': score,
                'tier': tier,
                'tier_description': tier_description,
                'breakdown': breakdown,
                'sku_count': brand_data.get('sku_count', 0),
                'has_enrichment': bool(brand_data.get('enrichment_data')),
                'class_types': json.loads(brand_data.get('class_types', '[]')) if brand_data.get('class_types') else [],
                'is_competitor_target': is_competitor  # Track poaching opportunities
            })

        # Sort by score descending
        ranked_brands.sort(key=lambda x: x['score'], reverse=True)

        conn.close()

        if limit:
            return ranked_brands[:limit]
        return ranked_brands

    def get_enrichment_queue(self, tier: int = 1, exclude_enriched: bool = True) -> List[Dict]:
        """
        Get brands for enrichment based on tier

        Args:
            tier: Tier level (1-5)
            exclude_enriched: Whether to exclude already enriched brands

        Returns:
            List of brands ready for enrichment
        """
        all_ranked = self.rank_all_brands()

        queue = []
        for brand in all_ranked:
            # Filter by tier
            if brand['tier'] != tier:
                continue

            # Skip if already enriched
            if exclude_enriched and brand['has_enrichment']:
                continue

            queue.append(brand)

        return queue

    def get_statistics(self) -> Dict:
        """Get ranking statistics"""
        all_ranked = self.rank_all_brands()

        stats = {
            'total_brands': len(all_ranked),
            'tier_distribution': {},
            'enriched_by_tier': {},
            'spirits_brands': 0,
            'wine_brands': 0,
            'beer_brands': 0,
            'competitor_target_brands': 0,  # MHW/Parkstreet brands to poach
            'brands_with_importers': 0,
            'brands_with_websites': 0  # Track brands ready for Apollo
        }

        # Count by tier
        for tier_num in range(1, 6):
            tier_brands = [b for b in all_ranked if b['tier'] == tier_num]
            stats['tier_distribution'][f'tier_{tier_num}'] = len(tier_brands)

            enriched = [b for b in tier_brands if b['has_enrichment']]
            stats['enriched_by_tier'][f'tier_{tier_num}'] = len(enriched)

        # Count by product type
        for brand in all_ranked:
            breakdown = brand['breakdown']

            # Product type analysis
            if breakdown['product_type'] >= 25:  # Spirits threshold
                stats['spirits_brands'] += 1
            elif breakdown['product_type'] >= 12:  # Wine threshold
                stats['wine_brands'] += 1
            elif breakdown['product_type'] >= 8:  # Beer threshold
                stats['beer_brands'] += 1

            # Competitor targets (MHW/Parkstreet brands to poach)
            if breakdown['competitor_target'] > 0:
                stats['competitor_target_brands'] += 1

            # Importers
            if breakdown['importer'] > 0 or breakdown['competitor_target'] > 0:
                stats['brands_with_importers'] += 1

            # Websites (for Apollo)
            if breakdown['has_website'] > 0:
                stats['brands_with_websites'] += 1

        return stats