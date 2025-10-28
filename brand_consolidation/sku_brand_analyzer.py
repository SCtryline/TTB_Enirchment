"""
Enhanced SKU vs Brand Consolidation Analyzer
Implements intelligent URL-based brand hierarchy detection and SKU consolidation logic
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse
from difflib import SequenceMatcher
from collections import defaultdict

logger = logging.getLogger(__name__)

class SKUBrandAnalyzer:
    """
    Analyzes brand consolidation opportunities with SKU vs Brand distinction

    Logic:
    1. If brands have same URL and one brand name matches domain → that's the parent brand, others are SKUs
    2. If brands have same URL but neither matches domain → portfolio company (sibling brands)
    3. If brand name similar to product names → brand is parent, products are SKUs
    4. Use enrichment confidence and completeness to determine hierarchy
    """

    def __init__(self, database_instance):
        self.db = database_instance
        self.domain_cache = {}

    def analyze_consolidation_opportunities(self, brands_data: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """
        OPTIMIZED: Enhanced consolidation analysis with SKU vs Brand detection
        Returns list of consolidation opportunities with hierarchy context
        """
        import time
        start_time = time.time()

        opportunities = []

        # OPTIMIZATION 1: Only analyze brands with URLs first (much smaller subset)
        brands_with_urls = self._filter_brands_with_urls(brands_data)
        logger.info(f"🔍 Analyzing {len(brands_with_urls)} brands with URLs (out of {len(brands_data)} total)")

        if len(brands_with_urls) == 0:
            logger.info("⚠️ No brands with URLs found - skipping URL-based analysis")
            return []

        # OPTIMIZATION 2: Group brands by domain first (efficient)
        domain_groups = self._group_brands_by_domain(brands_with_urls)
        logger.info(f"📊 Found {len(domain_groups)} domains with multiple brands")

        # OPTIMIZATION 3: Only analyze domains with 2+ brands
        for domain, brands_in_domain in domain_groups.items():
            if len(brands_in_domain) > 1:
                domain_opportunities = self._analyze_domain_group(domain, brands_in_domain, brands_with_urls)
                opportunities.extend(domain_opportunities)

        # OPTIMIZATION 4: Limit fuzzy matching to high-confidence brands only
        if len(opportunities) < 20:  # Only do fuzzy if we don't have many URL-based opportunities
            high_confidence_brands = {
                name: data for name, data in brands_with_urls.items()
                if self._get_enrichment_confidence(data) > 0.7
            }
            if len(high_confidence_brands) < 500:  # Limit fuzzy search scope
                fuzzy_opportunities = self._find_fuzzy_consolidation_opportunities(high_confidence_brands, domain_groups)
                opportunities.extend(fuzzy_opportunities[:10])  # Limit to top 10 fuzzy matches

        # Sort by confidence and impact
        opportunities.sort(key=lambda x: (x['confidence'], len(x['brands_to_consolidate'])), reverse=True)

        elapsed = time.time() - start_time
        logger.info(f"✅ SKU/Brand analysis completed in {elapsed:.2f}s: {len(opportunities)} opportunities found")

        return opportunities[:50]  # Return top 50 to prevent UI overload

    def _filter_brands_with_urls(self, brands_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """OPTIMIZATION: Pre-filter brands to only those with URLs (much smaller dataset)"""
        filtered_brands = {}

        for brand_name, brand_data in brands_data.items():
            url = self._get_brand_url(brand_data)
            if url:
                filtered_brands[brand_name] = brand_data

        return filtered_brands

    def _group_brands_by_domain(self, brands_data: Dict[str, Dict]) -> Dict[str, List[str]]:
        """Group brands by their website domain"""
        domain_groups = defaultdict(list)

        for brand_name, brand_data in brands_data.items():
            url = self._get_brand_url(brand_data)
            if url:
                domain = self._extract_domain(url)
                if domain:
                    domain_groups[domain].append(brand_name)

        # Only keep domains with multiple brands
        return {domain: brands for domain, brands in domain_groups.items() if len(brands) > 1}

    def _analyze_domain_group(self, domain: str, brand_names: List[str], brands_data: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """
        Analyze brands sharing the same domain to determine hierarchy
        """
        opportunities = []

        if len(brand_names) < 2:
            return opportunities

        # Extract domain name for matching
        domain_base = self._extract_domain_base_name(domain)

        # Find which brand(s) match the domain name
        domain_matching_brands = []
        sku_candidates = []

        for brand_name in brand_names:
            brand_data = brands_data[brand_name]

            # Check if brand name matches domain
            brand_similarity = self._calculate_domain_brand_similarity(domain_base, brand_name)

            if brand_similarity > 0.7:  # Strong match with domain
                domain_matching_brands.append({
                    'name': brand_name,
                    'similarity': brand_similarity,
                    'data': brand_data,
                    'enrichment_confidence': self._get_enrichment_confidence(brand_data)
                })
            else:
                sku_candidates.append({
                    'name': brand_name,
                    'similarity': brand_similarity,
                    'data': brand_data,
                    'enrichment_confidence': self._get_enrichment_confidence(brand_data)
                })

        # Determine consolidation strategy
        if domain_matching_brands and sku_candidates:
            # Case 1: Clear parent brand + SKUs
            parent_brand = max(domain_matching_brands, key=lambda x: (x['enrichment_confidence'], x['similarity']))

            # Generate unique proposal ID
            proposal_id = f"sku_to_brand_{domain.replace('.', '_')}_{len(sku_candidates)}_brands"

            opportunity = {
                'proposal_id': proposal_id,
                'type': 'brand_sku_consolidation',
                'consolidation_type': 'SKU_TO_BRAND',
                'canonical_name': parent_brand['name'],
                'brands_to_consolidate': [brand['name'] for brand in sku_candidates],
                'domain': domain,
                'confidence': 0.9,  # High confidence when domain matches
                'reasoning': f"Domain '{domain}' matches brand '{parent_brand['name']}' - others appear to be SKUs/products",
                'hierarchy': {
                    'parent_brand': parent_brand['name'],
                    'skus': [brand['name'] for brand in sku_candidates],
                    'relationship': 'Parent brand owns product SKUs'
                },
                'url_evidence': self._get_brand_url(parent_brand['data']),
                'similarity_scores': {
                    'parent_to_domain': parent_brand['similarity'],
                    'sku_similarities': [brand['similarity'] for brand in sku_candidates]
                }
            }
            opportunities.append(opportunity)

        elif len(brand_names) > 1 and not domain_matching_brands:
            # Case 2: Portfolio company - multiple brands under same company
            # Choose the brand with highest enrichment confidence as canonical
            brand_candidates = [
                {
                    'name': brand_name,
                    'data': brands_data[brand_name],
                    'enrichment_confidence': self._get_enrichment_confidence(brands_data[brand_name]),
                    'completeness_score': self._calculate_brand_completeness(brands_data[brand_name])
                }
                for brand_name in brand_names
            ]

            # Sort by enrichment confidence and completeness
            brand_candidates.sort(key=lambda x: (x['enrichment_confidence'], x['completeness_score']), reverse=True)
            canonical_brand = brand_candidates[0]

            # Generate unique proposal ID
            proposal_id = f"portfolio_{domain.replace('.', '_')}_{len(brand_names)}_brands"

            opportunity = {
                'proposal_id': proposal_id,
                'type': 'portfolio_consolidation',
                'consolidation_type': 'PORTFOLIO_BRANDS',
                'canonical_name': canonical_brand['name'],
                'brands_to_consolidate': [brand['name'] for brand in brand_candidates[1:]],
                'domain': domain,
                'confidence': 0.75,  # Medium-high confidence for portfolio
                'reasoning': f"Multiple brands under same domain '{domain}' - appears to be portfolio company",
                'hierarchy': {
                    'parent_brand': canonical_brand['name'],
                    'sibling_brands': [brand['name'] for brand in brand_candidates[1:]],
                    'relationship': 'Portfolio company with multiple brands'
                },
                'url_evidence': self._get_brand_url(canonical_brand['data']),
                'portfolio_analysis': {
                    'total_brands': len(brand_names),
                    'canonical_reasoning': 'Highest enrichment confidence and data completeness'
                }
            }
            opportunities.append(opportunity)

        return opportunities

    def _find_fuzzy_consolidation_opportunities(self, brands_data: Dict[str, Dict], domain_groups: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Find brands that should be consolidated based on name similarity (not domain)"""
        opportunities = []
        processed_brands = set()

        # Flatten domain groups to exclude them from fuzzy matching
        for brands_in_domain in domain_groups.values():
            processed_brands.update(brands_in_domain)

        brand_names = [name for name in brands_data.keys() if name not in processed_brands]

        for i, brand1 in enumerate(brand_names):
            if brand1 in processed_brands:
                continue

            similar_brands = [brand1]

            for j, brand2 in enumerate(brand_names[i+1:], i+1):
                if brand2 in processed_brands:
                    continue

                similarity = self._calculate_brand_name_similarity(brand1, brand2)

                if similarity > 0.8:  # High similarity threshold
                    similar_brands.append(brand2)

            if len(similar_brands) > 1:
                # Determine which should be canonical based on completeness and length
                canonical_brand = self._select_canonical_brand(similar_brands, brands_data)

                # Generate unique proposal ID
                proposal_id = f"similar_names_{canonical_brand.replace(' ', '_').lower()}_{len(similar_brands)}_variations"

                opportunity = {
                    'proposal_id': proposal_id,
                    'type': 'name_similarity_consolidation',
                    'consolidation_type': 'SIMILAR_NAMES',
                    'canonical_name': canonical_brand,
                    'brands_to_consolidate': [name for name in similar_brands if name != canonical_brand],
                    'domain': None,
                    'confidence': 0.6 + (len(similar_brands) * 0.1),  # Confidence increases with group size
                    'reasoning': f"Brand names are highly similar - likely variations of same brand",
                    'hierarchy': {
                        'parent_brand': canonical_brand,
                        'variations': [name for name in similar_brands if name != canonical_brand],
                        'relationship': 'Name variations of same brand'
                    },
                    'url_evidence': self._get_brand_url(brands_data.get(canonical_brand, {})),
                    'name_similarities': {
                        name: self._calculate_brand_name_similarity(canonical_brand, name)
                        for name in similar_brands if name != canonical_brand
                    }
                }
                opportunities.append(opportunity)
                processed_brands.update(similar_brands)

        return opportunities

    def _get_brand_url(self, brand_data: Dict) -> Optional[str]:
        """Extract URL from brand enrichment data"""
        enrichment = brand_data.get('enrichment_data')
        if not enrichment:
            return None

        # Handle both flat and nested structures
        if isinstance(enrichment, str):
            try:
                enrichment = json.loads(enrichment)
            except:
                return None

        return (enrichment.get('url') or
                enrichment.get('website', {}).get('url') if isinstance(enrichment.get('website'), dict) else None)

    def _extract_domain(self, url: str) -> str:
        """Extract clean domain from URL"""
        if not url:
            return ''

        try:
            parsed = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}')
            domain = parsed.netloc.lower()
            return domain.replace('www.', '')
        except:
            return ''

    def _extract_domain_base_name(self, domain: str) -> str:
        """Extract the base company name from domain"""
        if not domain:
            return ''

        # Remove TLD and common prefixes
        base = domain.split('.')[0]

        # Remove common business suffixes from domain
        suffixes_to_remove = ['brewing', 'brewery', 'winery', 'wines', 'spirits', 'distillery', 'company', 'co', 'inc']

        for suffix in suffixes_to_remove:
            if base.endswith(suffix):
                base = base[:-len(suffix)].rstrip('-_')
                break

        return base.replace('-', ' ').replace('_', ' ').strip().upper()

    def _calculate_domain_brand_similarity(self, domain_base: str, brand_name: str) -> float:
        """Calculate similarity between domain base name and brand name"""
        if not domain_base or not brand_name:
            return 0.0

        # Clean brand name
        brand_clean = brand_name.upper().strip()

        # Direct match
        if domain_base == brand_clean:
            return 1.0

        # Check if domain base is contained in brand name
        if domain_base in brand_clean:
            return 0.9

        # Check if brand name starts with domain base
        if brand_clean.startswith(domain_base):
            return 0.85

        # Fuzzy similarity
        return SequenceMatcher(None, domain_base, brand_clean).ratio()

    def _calculate_brand_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two brand names"""
        if not name1 or not name2:
            return 0.0

        # Normalize names
        norm1 = name1.upper().strip()
        norm2 = name2.upper().strip()

        # Exact match
        if norm1 == norm2:
            return 1.0

        # Use sequence matcher for fuzzy similarity
        return SequenceMatcher(None, norm1, norm2).ratio()

    def _get_enrichment_confidence(self, brand_data: Dict) -> float:
        """Get enrichment confidence score"""
        enrichment = brand_data.get('enrichment_data')
        if not enrichment:
            return 0.0

        if isinstance(enrichment, str):
            try:
                enrichment = json.loads(enrichment)
            except:
                return 0.0

        return enrichment.get('confidence', 0.0)

    def _calculate_brand_completeness(self, brand_data: Dict) -> float:
        """Calculate how complete/rich the brand data is"""
        score = 0.0

        # Check for various data fields
        if brand_data.get('countries'):
            score += 0.2
        if brand_data.get('class_types'):
            score += 0.2
        if brand_data.get('permit_numbers'):
            score += 0.2
        if brand_data.get('importers'):
            score += 0.2
        if brand_data.get('enrichment_data'):
            score += 0.2

        return score

    def _select_canonical_brand(self, brand_names: List[str], brands_data: Dict[str, Dict]) -> str:
        """Select the best canonical brand from a group"""
        candidates = []

        for brand_name in brand_names:
            brand_data = brands_data.get(brand_name, {})
            candidates.append({
                'name': brand_name,
                'completeness': self._calculate_brand_completeness(brand_data),
                'enrichment_confidence': self._get_enrichment_confidence(brand_data),
                'length': len(brand_name),  # Shorter names often better canonical
                'has_url': bool(self._get_brand_url(brand_data))
            })

        # Sort by: enrichment confidence, completeness, has URL, shorter name
        candidates.sort(key=lambda x: (
            x['enrichment_confidence'],
            x['completeness'],
            x['has_url'],
            -x['length']  # Negative for shorter names first
        ), reverse=True)

        return candidates[0]['name']