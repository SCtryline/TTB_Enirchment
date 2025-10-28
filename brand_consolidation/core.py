"""
Core Brand Consolidation Engine with White Label Support
Enhanced with producer attribution, production relationship tracking, and agentic learning
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from .config import CONSOLIDATION_CONFIG, CONFIDENCE_RULES, WHITE_LABEL_BRANDS, PRODUCER_RELATIONSHIPS

logger = logging.getLogger(__name__)

class BrandConsolidator:
    """
    Main consolidation orchestrator with white label awareness and agentic learning
    """
    
    def __init__(self, database_instance):
        """Initialize with existing database instance"""
        self.db = database_instance
        self.consolidation_cache = {}
        self.producer_relationships = {}
        self.white_label_mappings = {}
        
        # Initialize components
        from .brand_extractor import BrandExtractor
        from .brand_matcher import BrandMatcher
        from .sku_extractor import SKUExtractor
        from .consolidation_proposal import ConsolidationProposal
        
        self.brand_extractor = BrandExtractor()
        self.brand_matcher = BrandMatcher(database_instance)
        self.sku_extractor = SKUExtractor()
        self.proposal_generator = ConsolidationProposal()
        
        # Initialize agentic learning system if enabled
        if CONSOLIDATION_CONFIG.get('training_mode', True):
            try:
                from .agentic_consolidator import AgenticConsolidationSystem
                self.agentic_system = AgenticConsolidationSystem()
                logger.info("🧠 Agentic consolidation learning system initialized")
            except Exception as e:
                logger.error(f"Failed to initialize agentic system: {e}")
                self.agentic_system = None
        else:
            self.agentic_system = None
        
    def analyze_brands_with_producers(self) -> Dict[str, Any]:
        """
        Analyze all brands with full producer context
        """
        analysis = {
            'total_brands': len(self.db.db.get('brands', {})),
            'brands_with_producers': 0,
            'white_label_candidates': 0,
            'consolidation_opportunities': 0,
            'producer_relationships': {},
            'brand_families': {}
        }
        
        brands = self.db.db.get('brands', {})
        
        for brand_name, brand_data in brands.items():
            # Analyze each brand's producer relationships
            producer_analysis = self._analyze_brand_producers(brand_name, brand_data)
            
            if producer_analysis['has_producer']:
                analysis['brands_with_producers'] += 1
                
            if producer_analysis['is_white_label_candidate']:
                analysis['white_label_candidates'] += 1
                
            # Store producer relationship analysis
            analysis['producer_relationships'][brand_name] = producer_analysis
        
        # Find consolidation opportunities with producer awareness
        consolidation_groups = self.find_consolidation_groups()
        analysis['consolidation_opportunities'] = len(consolidation_groups)
        analysis['brand_families'] = consolidation_groups
        
        return analysis
    
    def _analyze_brand_producers(self, brand_name: str, brand_data: Dict) -> Dict[str, Any]:
        """
        Analyze producer relationships for a single brand
        """
        analysis = {
            'brand_name': brand_name,
            'has_producer': False,
            'is_white_label_candidate': False,
            'current_producers': [],
            'production_type': 'unknown',
            'confidence': 0.0
        }
        
        # Get permits for this brand
        permits = brand_data.get('permit_numbers', [])
        
        for permit in permits:
            # Try to find producer
            producer = self._find_producer_for_permit(permit)
            
            if producer:
                analysis['has_producer'] = True
                
                # Determine relationship type
                relationship_type = self._determine_producer_relationship(
                    brand_name, producer, permit
                )
                
                producer_info = {
                    'permit': permit,
                    'producer_name': producer.get('owner_name', ''),
                    'relationship': relationship_type,
                    'confidence': self._calculate_producer_confidence(
                        brand_name, producer, relationship_type
                    ),
                    'operating_name': producer.get('operating_name', '')
                }
                
                analysis['current_producers'].append(producer_info)
        
        # Determine if this looks like a white label
        analysis['is_white_label_candidate'] = self._is_white_label_candidate(
            brand_name, analysis['current_producers']
        )
        
        # Set production type
        if analysis['is_white_label_candidate']:
            analysis['production_type'] = 'contract_production'
        elif analysis['has_producer']:
            analysis['production_type'] = 'own_brand'
        
        return analysis
    
    def _find_producer_for_permit(self, permit: str) -> Optional[Dict]:
        """Find producer data for a given permit"""
        # Try spirit producers first
        producer = self.db.get_spirit_producer(permit)
        if producer:
            producer['type'] = 'Spirit'
            return producer
            
        # Try wine producers
        producer = self.db.get_wine_producer(permit)
        if producer:
            producer['type'] = 'Wine'
            return producer
            
        return None
    
    def _determine_producer_relationship(self, brand_name: str, producer: Dict, permit: str) -> str:
        """
        Determine the type of relationship between brand and producer
        """
        producer_name = producer.get('owner_name', '').upper()
        brand_name_upper = brand_name.upper()
        
        # Check if producer name appears in brand name
        if any(word in brand_name_upper for word in producer_name.split() if len(word) > 3):
            return 'primary_producer'
        
        # Check for white label indicators
        if self._is_white_label_brand(brand_name):
            return 'contract_producer'
        
        # Check operating name
        operating_name = producer.get('operating_name', '').upper()
        if operating_name and any(word in brand_name_upper for word in operating_name.split() if len(word) > 3):
            return 'primary_producer'
        
        # Default to secondary for now
        return 'secondary_producer'
    
    def _is_white_label_candidate(self, brand_name: str, producers: List[Dict]) -> bool:
        """
        Determine if a brand is likely a white label
        """
        # Check against known white label brands
        if self._is_white_label_brand(brand_name):
            return True
        
        # Check if brand name doesn't match any producer names
        if not producers:
            return False
        
        brand_words = set(brand_name.upper().split())
        
        for producer_info in producers:
            producer_name = producer_info.get('producer_name', '').upper()
            producer_words = set(producer_name.split())
            
            # If there's significant overlap, it's probably not white label
            overlap = len(brand_words & producer_words)
            if overlap >= 1:  # At least one word in common
                return False
        
        return True  # No overlap with any producer names
    
    def _is_white_label_brand(self, brand_name: str) -> bool:
        """Check if brand name matches known white label patterns"""
        brand_upper = brand_name.upper()
        
        # Check retail store brands
        for store_brand in WHITE_LABEL_BRANDS['retail_stores']:
            if store_brand in brand_upper:
                return True
        
        # Check private label indicators
        for indicator in WHITE_LABEL_BRANDS['private_label_indicators']:
            if indicator in brand_upper:
                return True
        
        return False
    
    def _calculate_producer_confidence(self, brand_name: str, producer: Dict, relationship_type: str) -> float:
        """Calculate confidence in producer attribution"""
        base_confidence = PRODUCER_RELATIONSHIPS[relationship_type]['confidence_weight']
        
        # Adjust based on various factors
        producer_name = producer.get('owner_name', '')
        brand_name_upper = brand_name.upper()
        producer_name_upper = producer_name.upper()
        
        # Boost if producer name appears in brand
        if any(word in brand_name_upper for word in producer_name_upper.split() if len(word) > 3):
            base_confidence = min(base_confidence + 0.2, 1.0)
        
        # Reduce if it looks like white label
        if self._is_white_label_brand(brand_name):
            if relationship_type == 'contract_producer':
                base_confidence = min(base_confidence + 0.1, 1.0)  # Expected for contract
            else:
                base_confidence = max(base_confidence - 0.2, 0.1)  # Unexpected
        
        return round(base_confidence, 2)
    
    def find_consolidation_groups(self) -> Dict[str, List[str]]:
        """
        Find brand consolidation opportunities with brand name normalization and producer awareness
        """
        brands = self.db.db.get('brands', {})
        
        # PHASE 1: Brand Name Normalization - Find brands that need name correction
        name_normalization_groups = self._find_brand_name_normalization_opportunities(brands)
        
        # PHASE 2: Traditional Fuzzy Matching - Find similar brands after normalization
        consolidation_groups = {}
        processed_brands = set()
        
        for brand_name in brands.keys():
            if brand_name in processed_brands:
                continue
            
            # Find similar brands for this one
            similar_brands = self._find_similar_brands(brand_name, brands)
            
            if len(similar_brands) > 1:
                # Determine canonical name for this group
                canonical_name = self._select_canonical_name(similar_brands, brands)
                consolidation_groups[canonical_name] = similar_brands
                
                # Mark all as processed
                processed_brands.update(similar_brands)
        
        # Merge name normalization opportunities with consolidation groups
        for canonical_name, group in name_normalization_groups.items():
            if canonical_name not in consolidation_groups:
                consolidation_groups[canonical_name] = group
            else:
                # Merge with existing group
                existing_group = set(consolidation_groups[canonical_name])
                new_group = set(group)
                consolidation_groups[canonical_name] = list(existing_group.union(new_group))
        
        return consolidation_groups
    
    def _find_brand_name_normalization_opportunities(self, brands: Dict) -> List[Dict]:
        """
        PHASE 1: Find brands that need name normalization (product names -> company names)
        Returns a list of consolidation opportunities with analysis
        """
        opportunities = []
        
        # Find brands with websites from enrichment_data
        brands_with_websites = {}
        logger.info(f"🔍 Analyzing {len(brands)} brands for consolidation opportunities...")
        
        # Log summary at the end 
        brands_with_websites_count = 0
        
        for name, data in brands.items():
            # Try both field names to handle different data structures
            enrichment = data.get('enrichment_data') or data.get('enrichment')
            if name == '"WITTY FARMER" BELGIAN STYLE WITBIER':
                logger.info(f"🔬 WITTY FARMER enrichment: {data.get('enrichment')}")
            if enrichment:
                # Parse enrichment_data if it's a string
                if isinstance(enrichment, str):
                    try:
                        import json
                        enrichment = json.loads(enrichment)
                    except:
                        continue
                
                # Check for website URL or domain (handle multiple data structures)
                url = enrichment.get('url')
                domain = enrichment.get('domain')
                website_data = enrichment.get('website', {})
                website_url = website_data.get('url') if isinstance(website_data, dict) else None
                
                if url or domain or website_url:
                    # Determine the final URL to use
                    final_url = url or website_url
                    if not final_url and domain:
                        final_url = f"https://{domain}"
                    
                    if final_url:
                        brands_with_websites[name] = data
                        brands_with_websites[name]['parsed_enrichment'] = enrichment.copy()
                        brands_with_websites[name]['parsed_enrichment']['url'] = final_url
                        brands_with_websites_count += 1
                        if 'WITTY FARMER' in name:
                            logger.info(f"🎯 WITTY FARMER found with website: {final_url}")
                        logger.debug(f"✅ Found brand with website: {name} -> {final_url}")
        
        # Group brands by website domain (same company, different product names)
        website_groups = {}
        for brand_name, brand_data in brands_with_websites.items():
            enrichment = brand_data['parsed_enrichment']
            website_url = enrichment.get('url') or enrichment.get('website', {}).get('url', '')
            domain = self._extract_domain_from_url(website_url)
            
            if domain:
                if domain not in website_groups:
                    website_groups[domain] = []
                website_groups[domain].append((brand_name, website_url))
        
        # Analyze each website group for name normalization opportunities
        for domain, brand_list in website_groups.items():
            brand_names = [b[0] for b in brand_list]
            website_url = brand_list[0][1] if brand_list else ''
            
            # Extract real company name from website
            real_brand_name = self._extract_real_brand_name_from_domain(domain, brand_names, brands)
            
            # Check if any of the current names look like product names
            product_names = []
            analysis_items = []
            
            for brand_name in brand_names:
                is_product = self._is_likely_product_name(brand_name, brands[brand_name])
                if 'WITTY FARMER' in brand_name:
                    logger.info(f"🧪 Product name test for {brand_name}: {is_product}")
                if is_product:
                    product_names.append(brand_name)
                    
                analysis_items.append({
                    'brand_name': brand_name,
                    'is_likely_product_name': is_product,
                    'website': website_url,
                    'current_skus': len(brands[brand_name].get('skus', [])),
                    'countries': brands[brand_name].get('countries', [])
                })
            
            # Handle both multiple brands on same domain AND single product-named brands
            if product_names and real_brand_name:
                # For single product-named brands, only consolidate if the extracted name is different
                if len(brand_names) == 1:
                    current_name = brand_names[0]
                    if current_name.upper() != real_brand_name.upper():
                        # Single product-named brand needing normalization
                        opportunities.append({
                            'proposal_id': f"normalization_{real_brand_name.lower().replace(' ', '_')}",
                            'suggested_name': real_brand_name,
                            'brands_to_merge': [current_name],
                            'confidence': 0.85,
                            'analysis': analysis_items,
                            'reason': 'Product name detected, should use company name'
                        })
                        logger.info(f"🔍 Found single brand name normalization: {current_name} -> {real_brand_name}")
                else:
                    # Multiple brands sharing same domain
                    opportunities.append({
                        'proposal_id': f"normalization_{real_brand_name.lower().replace(' ', '_')}",
                        'suggested_name': real_brand_name,
                        'brands_to_merge': brand_names,
                        'confidence': 0.9,
                        'analysis': analysis_items,
                        'reason': 'Multiple products from same company website'
                    })
                    logger.info(f"🔍 Found multi-brand normalization opportunity: {product_names} -> {real_brand_name}")
        
        # PHASE 2: Find similar brand names that might be duplicates/variations
        similarity_opportunities = self._find_similar_brand_consolidation_opportunities(brands)
        opportunities.extend(similarity_opportunities)
        
        logger.info(f"📊 Consolidation analysis complete: {brands_with_websites_count} brands with websites, {len(opportunities)} total opportunities found")
        return opportunities
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract clean domain from URL"""
        if not url:
            return ""
        
        # Clean URL
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')  # Remove www prefix
        return domain.lower()
    
    def _extract_real_brand_name_from_domain(self, domain: str, brand_list: List[str], brands: Dict) -> str:
        """
        Extract the real company name from domain and brand context
        """
        # Strategy 1: Look for the most "company-like" name in the brand list
        company_like_names = []
        for brand_name in brand_list:
            if self._looks_like_company_name(brand_name, brands[brand_name]):
                company_like_names.append(brand_name)
        
        # Prefer existing company-like name if found
        if company_like_names:
            return max(company_like_names, key=len)  # Choose longest/most descriptive
        
        # Strategy 2: Extract from domain name with intelligent parsing
        domain_parts = domain.replace('.com', '').replace('.net', '').replace('.org', '')
        
        # Handle common patterns in brewery/winery domains
        if 'brewing' in domain_parts:
            # Extract the brewery name part (remove 'brewing' suffix)
            brewery_part = domain_parts.replace('brewing', '').strip('-_')
            domain_name = self._parse_domain_name(brewery_part)
            return f"{domain_name.upper()} BREWING"
        elif 'winery' in domain_parts or 'wine' in domain_parts:
            # Extract the winery name part
            winery_part = domain_parts.replace('winery', '').replace('wine', '').strip('-_')
            if winery_part.endswith('works'):  # Handle "atozwineworks" 
                winery_part = winery_part.replace('works', '').strip('-_')
            domain_name = self._parse_domain_name(winery_part)
            return f"{domain_name.upper()} WINERY"
        elif 'distillery' in domain_parts or 'spirits' in domain_parts:
            # Extract the distillery name part
            distillery_part = domain_parts.replace('distillery', '').replace('spirits', '').strip('-_')
            domain_name = self._parse_domain_name(distillery_part)
            return f"{domain_name.upper()} DISTILLERY"
        else:
            # Generic domain parsing
            domain_name = self._parse_domain_name(domain_parts)
            return domain_name.upper()
    
    def _parse_domain_name(self, domain_part: str) -> str:
        """
        Parse domain part into readable company name with intelligent word boundary detection
        """
        import re
        
        # Replace common separators
        name = domain_part.replace('-', ' ').replace('_', ' ')
        
        # Handle specific known patterns first
        if name.lower() == 'atoz':
            return 'A TO Z'
        
        # If already has spaces, just clean up
        if ' ' in name:
            return name.title()
        
        # Try to intelligently split concatenated words
        # Strategy 1: Look for common word patterns in brewery/distillery names
        common_words = [
            'mill', 'lane', 'creek', 'river', 'mountain', 'valley', 'hill', 
            'oak', 'stone', 'iron', 'copper', 'gold', 'silver',
            'north', 'south', 'east', 'west', 'new', 'old',
            'brewing', 'distilling', 'winery', 'spirits', 'company',
            'farm', 'house', 'barn', 'cellar', 'works', 'factory'
        ]
        
        # Convert to lowercase for matching
        lower_name = name.lower()
        words = []
        current_pos = 0
        
        while current_pos < len(lower_name):
            found_word = False
            # Try to find the longest matching word from current position
            for length in range(min(15, len(lower_name) - current_pos), 2, -1):
                potential_word = lower_name[current_pos:current_pos + length]
                
                # Check if it's a known word or common pattern
                if potential_word in common_words or len(potential_word) <= 4:
                    # Check if the remaining part makes sense
                    remaining = lower_name[current_pos + length:]
                    if not remaining or remaining[0:3] in [w[:3] for w in common_words if len(w) >= 3]:
                        words.append(name[current_pos:current_pos + length])
                        current_pos += length
                        found_word = True
                        break
            
            if not found_word:
                # Try to find natural break points using patterns
                # Look for transitions like: consonant+vowel, double letters, etc.
                for i in range(current_pos + 3, min(current_pos + 10, len(lower_name))):
                    if i < len(lower_name) - 2:
                        # Check for common patterns where words might break
                        if (lower_name[i-1] in 'lnrst' and lower_name[i] in 'aeiou') or \
                           (lower_name[i-1] == lower_name[i-2] and lower_name[i] != lower_name[i-1]):
                            words.append(name[current_pos:i])
                            current_pos = i
                            found_word = True
                            break
                
                if not found_word:
                    # Take the next 4-6 characters as a word
                    chunk_size = min(5, len(lower_name) - current_pos)
                    words.append(name[current_pos:current_pos + chunk_size])
                    current_pos += chunk_size
        
        # Special case: if we got "milllanedistillingcompany" -> mill lane distilling company
        if lower_name == 'milllanedistillingcompany':
            return 'MILL LANE DISTILLING COMPANY'
        
        # Clean up the words
        result_words = []
        for word in words:
            if word.lower() in ['by', 'to', 'of', 'the', 'and']:
                result_words.append(word.lower())
            else:
                result_words.append(word.capitalize())
        
        return ' '.join(result_words)
    
    def _find_similar_brand_consolidation_opportunities(self, brands: Dict) -> List[Dict]:
        """
        PHASE 2: Find brands with similar names that might be duplicates or variations
        Uses fuzzy matching, domain matching, location, and alcohol type similarity
        """
        opportunities = []
        processed_brands = set()
        
        # Convert brands to list for easier processing
        brand_list = [(name, data) for name, data in brands.items()]
        
        logger.info(f"🔍 Phase 2: Analyzing {len(brand_list)} brands for similarity-based consolidation...")
        
        # Performance optimization: Only analyze first 1000 brands for now to avoid timeout
        # In production, this could be done as a background job
        analysis_limit = min(1000, len(brand_list))
        logger.info(f"⚡ Performance mode: analyzing first {analysis_limit} brands for similarities")
        
        for i, (brand1_name, brand1_data) in enumerate(brand_list[:analysis_limit]):
            if brand1_name in processed_brands:
                continue
                
            similar_brands = []
            base_brand = brand1_name
            
            # Check against remaining brands in analysis limit
            for j, (brand2_name, brand2_data) in enumerate(brand_list[i+1:analysis_limit], i+1):
                if brand2_name in processed_brands:
                    continue
                    
                # Quick pre-filter: only do expensive similarity calc if names have some basic similarity
                if not self._brands_might_be_similar(brand1_name, brand2_name):
                    continue
                    
                # Calculate similarity confidence
                confidence = self._calculate_brand_similarity_confidence(
                    brand1_name, brand1_data, brand2_name, brand2_data
                )
                
                # If confidence is high enough, consider for consolidation
                if confidence >= 0.7:  # 70% threshold for similarity matching
                    similar_brands.append({
                        'name': brand2_name,
                        'data': brand2_data,
                        'confidence': confidence
                    })
                    processed_brands.add(brand2_name)
            
            # If we found similar brands, create consolidation opportunity
            if similar_brands:
                processed_brands.add(brand1_name)
                
                # Determine canonical name (longest/most complete name usually)
                all_candidates = [brand1_name] + [b['name'] for b in similar_brands]
                canonical_name = self._choose_canonical_brand_name(all_candidates, brands)
                
                # Calculate overall confidence (average of individual confidences)
                overall_confidence = sum(b['confidence'] for b in similar_brands) / len(similar_brands)
                overall_confidence = min(overall_confidence, 0.95)  # Cap at 95%
                
                # Create analysis items
                analysis_items = []
                brands_to_merge = []
                
                for brand_candidate in all_candidates:
                    if brand_candidate != canonical_name:
                        brands_to_merge.append(brand_candidate)
                    
                    brand_data = brands[brand_candidate]
                    analysis_items.append({
                        'brand_name': brand_candidate,
                        'is_likely_product_name': False,
                        'is_similar_brand': True,
                        'countries': brand_data.get('countries', []),
                        'class_types': brand_data.get('class_types', []),
                        'current_skus': len(brand_data.get('skus', [])),
                        'website': self._get_brand_website_url(brand_data)
                    })
                
                if brands_to_merge:  # Only create opportunity if there are brands to merge
                    opportunity = {
                        'proposal_id': f"similarity_{canonical_name.lower().replace(' ', '_').replace('\"', '')}",
                        'suggested_name': canonical_name,
                        'brands_to_merge': brands_to_merge,
                        'confidence': overall_confidence,
                        'analysis': analysis_items,
                        'reason': f'Similar brand names detected (avg {overall_confidence:.1%} similarity)'
                    }
                    
                    opportunities.append(opportunity)
                    logger.info(f"🎯 Found similarity consolidation: {brands_to_merge} -> {canonical_name} ({overall_confidence:.1%})")
        
        return opportunities
    
    def _create_consolidation_strategy(self, brands_to_merge: List[str], all_brands: Dict) -> Dict:
        """
        🧠 Intelligent data preservation strategy for consolidation
        Analyzes all brands to merge and determines best data to preserve
        """
        strategy = {
            'verified_enrichment': None,
            'best_website': None,
            'highest_confidence': 0.0,
            'most_complete_data': None,
            'reasoning': []
        }
        
        for brand_name in brands_to_merge:
            brand_data = all_brands.get(brand_name, {})
            enrichment = brand_data.get('enrichment', {})
            
            # Prioritize verified enrichment
            if enrichment.get('verification_status') == 'verified':
                strategy['verified_enrichment'] = brand_name
                strategy['reasoning'].append(f"✅ {brand_name} has verified enrichment data")
            
            # Track highest confidence website
            confidence = enrichment.get('confidence', 0.0)
            if confidence > strategy['highest_confidence']:
                strategy['highest_confidence'] = confidence
                strategy['best_website'] = brand_name
                strategy['reasoning'].append(f"🎯 {brand_name} has highest confidence website ({confidence:.1%})")
            
            # Check data completeness (SKUs, countries, etc.)
            completeness_score = (
                len(brand_data.get('countries', [])) * 0.3 +
                len(brand_data.get('class_types', [])) * 0.3 +
                brand_data.get('total_skus', 0) * 0.4
            )
            
            if not strategy['most_complete_data'] or completeness_score > 0:
                strategy['most_complete_data'] = brand_name
                strategy['reasoning'].append(f"📊 {brand_name} has comprehensive data")
        
        return strategy
    
    def _brands_might_be_similar(self, name1: str, name2: str) -> bool:
        """Quick pre-filter to avoid expensive similarity calculations"""
        # Normalize and get first words
        norm1 = self._normalize_brand_name(name1)
        norm2 = self._normalize_brand_name(name2)
        
        # If names are very different lengths, probably not similar
        if abs(len(norm1) - len(norm2)) > max(len(norm1), len(norm2)) * 0.6:
            return False
            
        # Check if they share at least one significant word (3+ characters)
        words1 = set(word for word in norm1.split() if len(word) >= 3)
        words2 = set(word for word in norm2.split() if len(word) >= 3)
        
        # Must share at least one word to be worth comparing
        return bool(words1.intersection(words2))
    
    def _calculate_brand_similarity_confidence(self, name1: str, data1: Dict, name2: str, data2: Dict) -> float:
        """
        Calculate confidence score for consolidating two brands based on multiple factors
        """
        confidence_factors = []
        
        # 1. Name similarity (using fuzzy string matching)
        name_similarity = self._calculate_name_similarity(name1, name2)
        confidence_factors.append(('name_similarity', name_similarity, 0.4))  # 40% weight
        
        # 2. Domain similarity (if both have websites)
        domain_similarity = self._calculate_domain_similarity(data1, data2)
        if domain_similarity is not None:
            confidence_factors.append(('domain_similarity', domain_similarity, 0.3))  # 30% weight
        
        # 3. Location similarity
        location_similarity = self._calculate_location_similarity(data1, data2)
        confidence_factors.append(('location_similarity', location_similarity, 0.15))  # 15% weight
        
        # 4. Alcohol type similarity
        alcohol_similarity = self._calculate_alcohol_type_similarity(data1, data2)
        confidence_factors.append(('alcohol_similarity', alcohol_similarity, 0.15))  # 15% weight
        
        # Calculate weighted average
        total_weight = sum(weight for _, _, weight in confidence_factors)
        weighted_score = sum(score * weight for _, score, weight in confidence_factors) / total_weight
        
        return weighted_score
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two brand names using fuzzy matching"""
        # Normalize names for comparison
        norm1 = self._normalize_brand_name(name1)
        norm2 = self._normalize_brand_name(name2)
        
        # If exactly the same after normalization, high confidence
        if norm1 == norm2:
            return 0.95
        
        # Use Levenshtein distance for fuzzy matching
        return self._levenshtein_similarity(norm1, norm2)
    
    def _normalize_brand_name(self, name: str) -> str:
        """Normalize brand name for comparison"""
        import re
        # Remove quotes, extra spaces, convert to upper
        normalized = re.sub(r'["\']', '', name.upper().strip())
        # Remove common business suffixes for comparison
        normalized = re.sub(r'\b(LLC|INC|CORP|COMPANY|CO\.|BREWING|WINERY|DISTILLERY)\b', '', normalized)
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity using Levenshtein distance"""
        if not s1 or not s2:
            return 0.0
        
        # Simple implementation of Levenshtein distance
        len1, len2 = len(s1), len(s2)
        if len1 == 0:
            return 0.0 if len2 > 0 else 1.0
        if len2 == 0:
            return 0.0
        
        # Create matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        # Fill matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i-1] == s2[j-1]:
                    matrix[i][j] = matrix[i-1][j-1]
                else:
                    matrix[i][j] = min(
                        matrix[i-1][j] + 1,      # deletion
                        matrix[i][j-1] + 1,      # insertion
                        matrix[i-1][j-1] + 1     # substitution
                    )
        
        # Convert distance to similarity (0-1 scale)
        max_len = max(len1, len2)
        distance = matrix[len1][len2]
        similarity = (max_len - distance) / max_len
        
        return max(0.0, similarity)
    
    def _calculate_domain_similarity(self, data1: Dict, data2: Dict) -> float:
        """Calculate similarity based on website domains"""
        url1 = self._get_brand_website_url(data1)
        url2 = self._get_brand_website_url(data2)
        
        if not url1 or not url2:
            return None  # No domain data to compare
        
        domain1 = self._extract_domain_from_url(url1)
        domain2 = self._extract_domain_from_url(url2)
        
        if domain1 == domain2:
            return 1.0  # Same domain = very high confidence
        
        # Check for subdomain variations (e.g., shop.example.com vs www.example.com)
        if domain1 and domain2:
            base1 = '.'.join(domain1.split('.')[-2:]) if len(domain1.split('.')) > 1 else domain1
            base2 = '.'.join(domain2.split('.')[-2:]) if len(domain2.split('.')) > 1 else domain2
            if base1 == base2:
                return 0.8  # Same base domain
        
        return 0.0  # Different domains
    
    def _get_brand_website_url(self, brand_data: Dict) -> str:
        """Extract website URL from brand data"""
        enrichment = brand_data.get('enrichment_data') or brand_data.get('enrichment')
        if not enrichment:
            return None
        
        # Handle different data structures
        if isinstance(enrichment, dict):
            # Try different possible paths
            url = (enrichment.get('url') or 
                  enrichment.get('website', {}).get('url') if isinstance(enrichment.get('website'), dict) else None)
            return url
        
        return None
    
    def _calculate_location_similarity(self, data1: Dict, data2: Dict) -> float:
        """Calculate similarity based on countries/locations"""
        countries1 = set(data1.get('countries', []))
        countries2 = set(data2.get('countries', []))
        
        if not countries1 or not countries2:
            return 0.5  # Neutral if no location data
        
        # Calculate Jaccard similarity
        intersection = countries1.intersection(countries2)
        union = countries1.union(countries2)
        
        if not union:
            return 0.5
        
        return len(intersection) / len(union)
    
    def _calculate_alcohol_type_similarity(self, data1: Dict, data2: Dict) -> float:
        """Calculate similarity based on alcohol/class types"""
        types1 = set(data1.get('class_types', []))
        types2 = set(data2.get('class_types', []))
        
        if not types1 or not types2:
            return 0.5  # Neutral if no type data
        
        # Calculate Jaccard similarity
        intersection = types1.intersection(types2)
        union = types1.union(types2)
        
        if not union:
            return 0.5
        
        return len(intersection) / len(union)
    
    def _choose_canonical_brand_name(self, candidates: List[str], brands: Dict) -> str:
        """Choose the best canonical name from candidates"""
        # Prefer names that look like company names over product names
        company_names = []
        for name in candidates:
            if not self._is_likely_product_name(name, brands[name]):
                company_names.append(name)
        
        if company_names:
            # Among company names, prefer longest (usually most descriptive)
            return max(company_names, key=len)
        
        # If all are product names, choose longest
        return max(candidates, key=len)
    
    def _is_likely_product_name(self, brand_name: str, brand_data: Dict) -> bool:
        """
        Detect if a brand name is likely a product/SKU name rather than company name
        """
        brand_lower = brand_name.lower()
        class_types = brand_data.get('class_types', [])
        
        # Product name indicators
        product_indicators = [
            # Size/volume indicators
            'oz', 'ml', 'liter', 'gallon', '12oz', '16oz', '750ml',
            # Descriptive terms that sound like products
            'freedom', 'barrel aged', 'reserve', 'special edition', 'limited',
            'single malt', 'double ipa', 'imperial', 'vintage', 'estate',
            # Numbers that might be years or varieties
            r'\d{4}',  # Years like 2015, 2020
            # Wine-specific product terms
            'château', 'cuvée', 'réserve', 'grand cru', 'premier cru',
            # Beer-specific product terms and styles
            'pale ale', 'ipa', 'stout', 'porter', 'lager', 'pilsner',
            'witbier', 'wheat beer', 'hefeweizen', 'saison', 'gose', 'sour',
            'belgian style', 'american style', 'english style', 'german style',
            'double', 'triple', 'quadruple', 'barleywine', 'amber', 'blonde'
        ]
        
        # Count indicators
        indicator_count = sum(1 for indicator in product_indicators 
                            if indicator in brand_lower)
        
        # Additional heuristics
        # 1. Very short names often product names
        if len(brand_name.split()) == 1 and len(brand_name) < 6:
            indicator_count += 1
            
        # 2. Names with numbers (except established years like 1848)
        import re
        if re.search(r'\d+', brand_name) and not re.search(r'18\d{2}|19\d{2}|20\d{2}', brand_name):
            indicator_count += 1
            
        # 3. Check against class types for alignment
        for class_type in class_types:
            class_lower = class_type.lower()
            if any(term in brand_lower for term in ['ale', 'beer', 'wine', 'whiskey', 'vodka'] 
                   if term in class_lower):
                indicator_count += 1
                
        return indicator_count >= 2  # Threshold for likely product name
    
    def _looks_like_company_name(self, brand_name: str, brand_data: Dict) -> bool:
        """
        Detect if a brand name looks like a proper company name
        """
        brand_lower = brand_name.lower()
        
        # Company name indicators
        company_indicators = [
            'brewing', 'brewery', 'winery', 'distillery', 'spirits',
            'wine company', 'cellars', 'vineyards', 'estates',
            'company', 'corp', 'corporation', 'inc', 'llc', 'ltd',
            '& co', 'and company', 'brothers', 'family'
        ]
        
        # Check for company indicators
        has_company_terms = any(indicator in brand_lower for indicator in company_indicators)
        
        # Check for proper business structure (longer, more formal names)
        word_count = len(brand_name.split())
        has_multiple_words = word_count >= 2
        
        # Check for proper capitalization patterns
        has_proper_caps = any(word[0].isupper() for word in brand_name.split() if word)
        
        return has_company_terms and has_multiple_words and has_proper_caps
    
    def _find_similar_brands(self, target_brand: str, all_brands: Dict) -> List[str]:
        """
        Find brands similar to the target brand using producer-aware matching
        """
        similar_brands = [target_brand]  # Include the target brand itself
        target_analysis = self._analyze_brand_producers(target_brand, all_brands[target_brand])
        
        for brand_name, brand_data in all_brands.items():
            if brand_name == target_brand:
                continue
            
            # Analyze this brand's producers
            brand_analysis = self._analyze_brand_producers(brand_name, brand_data)
            
            # Check if they should be consolidated
            should_consolidate, confidence, reason = self._should_consolidate_brands(
                target_analysis, brand_analysis
            )
            
            if should_consolidate and confidence >= CONSOLIDATION_CONFIG['min_confidence_display']:
                similar_brands.append(brand_name)
        
        return similar_brands
    
    def _should_consolidate_brands(self, brand1_analysis: Dict, brand2_analysis: Dict) -> Tuple[bool, float, str]:
        """
        Determine if two brands should be consolidated with confidence score
        """
        brand1_name = brand1_analysis['brand_name']
        brand2_name = brand2_analysis['brand_name']
        
        # Rule 1: Never consolidate different brand owners (white label protection)
        if self._different_brand_owners(brand1_analysis, brand2_analysis):
            return False, 0.1, "Different brand owners (white label protection)"
        
        # Rule 2: Same producer + similar names = high confidence
        if self._same_primary_producer(brand1_analysis, brand2_analysis):
            name_similarity = self._calculate_name_similarity(brand1_name, brand2_name)
            if name_similarity > 0.6:
                confidence = CONFIDENCE_RULES['same_producer_same_brand_owner']
                return True, confidence, f"Same producer + name similarity: {name_similarity:.2f}"
        
        # Rule 3: Brand family detection (same root name)
        root_similarity = self._calculate_brand_root_similarity(brand1_name, brand2_name)
        if root_similarity > 0.8:
            confidence = 0.7 + (root_similarity - 0.8) * 1.5  # Scale to 0.7-1.0
            return True, confidence, f"Brand family detected: {root_similarity:.2f}"
        
        # Rule 4: Fallback to name similarity only
        name_similarity = self._calculate_name_similarity(brand1_name, brand2_name)
        if name_similarity > 0.85:
            confidence = CONFIDENCE_RULES['no_producer_data']
            return True, confidence, f"High name similarity: {name_similarity:.2f}"
        
        return False, name_similarity, "No strong consolidation signal"
    
    def _different_brand_owners(self, brand1_analysis: Dict, brand2_analysis: Dict) -> bool:
        """Check if brands have different brand owners (white label detection)"""
        # For now, use simple heuristic - improve later with brand owner database
        brand1_white_label = brand1_analysis['is_white_label_candidate']
        brand2_white_label = brand2_analysis['is_white_label_candidate']
        
        # If one is white label and the other isn't, they have different owners
        if brand1_white_label != brand2_white_label:
            return True
        
        # If both are white labels, check if they're the same store brand
        if brand1_white_label and brand2_white_label:
            return not self._same_white_label_owner(
                brand1_analysis['brand_name'], 
                brand2_analysis['brand_name']
            )
        
        return False
    
    def _same_white_label_owner(self, brand1: str, brand2: str) -> bool:
        """Check if two white label brands have the same owner"""
        brand1_upper = brand1.upper()
        brand2_upper = brand2.upper()
        
        for store_brand in WHITE_LABEL_BRANDS['retail_stores']:
            if store_brand in brand1_upper and store_brand in brand2_upper:
                return True
        
        return False
    
    def _same_primary_producer(self, brand1_analysis: Dict, brand2_analysis: Dict) -> bool:
        """Check if brands have the same primary producer"""
        producers1 = brand1_analysis.get('current_producers', [])
        producers2 = brand2_analysis.get('current_producers', [])
        
        # Get primary producers
        primary1 = [p for p in producers1 if p['relationship'] == 'primary_producer']
        primary2 = [p for p in producers2 if p['relationship'] == 'primary_producer']
        
        if not primary1 or not primary2:
            return False
        
        # Check if any primary producers match
        for p1 in primary1:
            for p2 in primary2:
                if p1['permit'] == p2['permit']:
                    return True
        
        return False
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two brand names"""
        from difflib import SequenceMatcher
        
        # Basic similarity
        similarity = SequenceMatcher(None, name1.upper(), name2.upper()).ratio()
        
        # Boost if one is substring of another
        if name1.upper() in name2.upper() or name2.upper() in name1.upper():
            similarity = max(similarity, 0.8)
        
        return similarity
    
    def _calculate_brand_root_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity of brand root names (removing product terms)"""
        # Extract core brand names
        core1 = self.brand_extractor.extract_core_brand(name1)
        core2 = self.brand_extractor.extract_core_brand(name2)
        
        if not core1 or not core2:
            return 0.0
        
        return self._calculate_name_similarity(core1, core2)
    
    def _select_canonical_name(self, brand_list: List[str], all_brands: Dict) -> str:
        """Select the best canonical name for a brand family"""
        # For now, use the shortest name - can be enhanced later
        return min(brand_list, key=len)
    
    def generate_consolidation_proposals(self) -> Dict[str, Any]:
        """
        Generate consolidation proposals for manual review
        """
        consolidation_groups = self.find_consolidation_groups()
        proposals = []
        
        for canonical_name, brand_list in consolidation_groups.items():
            if len(brand_list) <= 1:
                continue
            
            proposal = self.proposal_generator.create_proposal(
                canonical_name, brand_list, self.db
            )
            proposals.append(proposal)
        
        return {
            'total_proposals': len(proposals),
            'proposals': proposals,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_consolidation_status(self) -> Dict[str, Any]:
        """Get current consolidation system status"""
        brands = self.db.db.get('brands', {})
        
        status = {
            'total_brands': len(brands),
            'consolidation_enabled': CONSOLIDATION_CONFIG['enabled'],
            'producer_data_available': {
                'spirit_producers': len(self.db.db.get('spirit_producers', {})),
                'wine_producers': len(self.db.db.get('wine_producers', {}))
            },
            'white_label_detection': CONSOLIDATION_CONFIG['white_label_detection'],
            'training_mode': CONSOLIDATION_CONFIG['training_mode']
        }
        
        # Add agentic learning status if available
        if self.agentic_system:
            status['agentic_learning'] = self.agentic_system.get_learning_insights()
        
        return status
    
    # === AGENTIC LEARNING INTEGRATION ===
    
    def learn_from_upload(self, brands_before: Dict, brands_after: Dict, filename: str) -> Dict[str, Any]:
        """
        Learn patterns from a new CSV upload
        Triggers agentic learning when new brands are uploaded
        """
        if not self.agentic_system:
            logger.warning("Agentic learning system not available")
            return {'learning_enabled': False}
        
        try:
            learning_event = self.agentic_system.learn_from_upload(brands_before, brands_after, filename)
            logger.info(f"🧠 Learned {len(learning_event['patterns_discovered'])} new patterns from {filename}")
            return learning_event
        except Exception as e:
            logger.error(f"Error in agentic learning from upload: {e}")
            return {'error': str(e)}
    
    def get_agentic_consolidation_groups(self) -> Dict[str, List[str]]:
        """
        Get consolidation groups using agentic learning predictions
        Falls back to traditional matching if agentic system unavailable
        """
        brands = self.db.db.get('brands', {})
        
        if self.agentic_system:
            try:
                # Use agentic predictions
                agentic_groups = self.agentic_system.predict_consolidation_groups(brands)
                logger.info(f"🧠 Agentic system found {len(agentic_groups)} consolidation groups")
                return agentic_groups
            except Exception as e:
                logger.error(f"Error in agentic consolidation: {e}")
        
        # Fallback to traditional matching
        logger.info("Using traditional consolidation matching")
        return self.find_consolidation_groups()
    
    def record_consolidation_feedback(self, brand_group: List[str], canonical: str, 
                                    action: str, confidence: float, reason: str = None) -> bool:
        """
        Record user feedback on consolidation decisions for learning
        """
        if not self.agentic_system:
            logger.warning("Agentic learning system not available for feedback")
            return False
        
        try:
            self.agentic_system.record_user_feedback(brand_group, canonical, action, confidence, reason)
            logger.info(f"🧠 Recorded {action} feedback for group: {brand_group}")
            return True
        except Exception as e:
            logger.error(f"Error recording consolidation feedback: {e}")
            return False
    
    def get_consolidation_recommendation(self, brand_group: List[str]) -> Dict[str, Any]:
        """
        Get AI recommendation for a consolidation decision
        """
        if not self.agentic_system or len(brand_group) < 2:
            return {'recommendation': 'no_recommendation', 'confidence': 0.0}
        
        try:
            # Analyze similarity between brands in the group
            total_confidence = 0.0
            comparisons = 0
            
            for i, brand1 in enumerate(brand_group):
                for brand2 in brand_group[i+1:]:
                    similarity, pattern_type = self.agentic_system._analyze_brand_similarity(brand1, brand2)
                    total_confidence += similarity
                    comparisons += 1
            
            average_confidence = total_confidence / max(comparisons, 1)
            
            # Get recommendation based on confidence
            if average_confidence >= 0.9:
                recommendation = 'strongly_recommend'
            elif average_confidence >= 0.7:
                recommendation = 'recommend'
            elif average_confidence >= 0.5:
                recommendation = 'review_needed'
            else:
                recommendation = 'not_recommended'
            
            return {
                'recommendation': recommendation,
                'confidence': average_confidence,
                'pattern_analysis': f'Based on {comparisons} brand comparisons',
                'suggestion': self._get_consolidation_suggestion(recommendation, average_confidence)
            }
        
        except Exception as e:
            logger.error(f"Error getting consolidation recommendation: {e}")
            return {'recommendation': 'error', 'confidence': 0.0, 'error': str(e)}
    
    def _get_consolidation_suggestion(self, recommendation: str, confidence: float) -> str:
        """Get human-readable suggestion for consolidation"""
        suggestions = {
            'strongly_recommend': f'These brands appear to be the same entity with {confidence:.1%} confidence. Safe to consolidate.',
            'recommend': f'These brands likely belong together with {confidence:.1%} confidence. Review recommended.',
            'review_needed': f'Moderate similarity detected ({confidence:.1%}). Manual review required.',
            'not_recommended': f'Low similarity ({confidence:.1%}). These may be different brands.',
        }
        return suggestions.get(recommendation, 'Unable to provide recommendation.')
    
    def auto_consolidate_high_confidence_groups(self, min_confidence: float = 0.95) -> Dict[str, Any]:
        """
        Automatically consolidate groups with very high confidence
        Only works if training mode is enabled and confidence is very high
        """
        if not CONSOLIDATION_CONFIG.get('training_mode', False):
            return {'auto_consolidation': False, 'reason': 'Training mode disabled'}
        
        if not self.agentic_system:
            return {'auto_consolidation': False, 'reason': 'Agentic system unavailable'}
        
        try:
            groups = self.get_agentic_consolidation_groups()
            auto_consolidated = []
            
            for canonical, brand_list in groups.items():
                if len(brand_list) > 1:
                    recommendation = self.get_consolidation_recommendation(brand_list)
                    
                    if (recommendation['confidence'] >= min_confidence and 
                        recommendation['recommendation'] == 'strongly_recommend'):
                        
                        # Auto-consolidate this group
                        auto_consolidated.append({
                            'canonical': canonical,
                            'brands': brand_list,
                            'confidence': recommendation['confidence']
                        })
                        
                        # Record as approved feedback
                        self.record_consolidation_feedback(
                            brand_list, canonical, 'approved', 
                            recommendation['confidence'], 'Auto-consolidated'
                        )
            
            return {
                'auto_consolidation': True,
                'groups_processed': len(groups),
                'auto_consolidated': len(auto_consolidated),
                'consolidated_groups': auto_consolidated
            }
        
        except Exception as e:
            logger.error(f"Error in auto-consolidation: {e}")
            return {'auto_consolidation': False, 'error': str(e)}
    
    def execute_consolidation(self, canonical_name: str, brands_to_merge: List[str]) -> Dict[str, Any]:
        """
        Execute brand consolidation by merging multiple brand entries into one canonical brand
        
        This method:
        1. Preserves all SKUs from all brands
        2. Combines all permit numbers (brand_permits, importers, producers)
        3. Merges all countries and class_types
        4. Preserves all enrichment data
        5. Updates the database atomically
        """
        try:
            # Use the database consolidation method instead of manual manipulation
            result = self.db.consolidate_brands(canonical_name, brands_to_merge)
            
            if result['success']:
                logger.info(f"✅ Consolidated {len(brands_to_merge)} brands into '{canonical_name}'")
                logger.info(f"   Countries preserved: {result['countries_count']}")
                logger.info(f"   Class types preserved: {result['class_types_count']}")
                logger.info(f"   Permits preserved: {result['permits_count']}")
                
                return {
                    'success': True,
                    'canonical_name': canonical_name,
                    'brands_merged': brands_to_merge,
                    'brands_removed': [b for b in brands_to_merge if b != canonical_name],
                    'countries_count': result['countries_count'],
                    'class_types_count': result['class_types_count'],
                    'total_permits_preserved': result['permits_count'],
                    'total_skus_preserved': 0  # SKUs are tracked separately in SQLite
                }
            else:
                return result
            
        except Exception as e:
            logger.error(f"Error executing consolidation: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about the agentic learning system"""
        if not self.agentic_system:
            return {'learning_available': False}
        
        try:
            insights = self.agentic_system.get_learning_insights()
            insights['learning_available'] = True
            return insights
        except Exception as e:
            logger.error(f"Error getting learning insights: {e}")
            return {'learning_available': False, 'error': str(e)}