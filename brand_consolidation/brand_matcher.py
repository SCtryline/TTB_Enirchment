"""
Brand Matcher - Advanced brand matching with producer awareness and white label support
Groups similar brands while respecting brand owner boundaries
"""

from typing import Dict, List, Tuple, Set, Optional
from difflib import SequenceMatcher
from .config import CONFIDENCE_RULES, WHITE_LABEL_BRANDS
from .brand_extractor import BrandExtractor

class BrandMatcher:
    """Group similar brands together using producer awareness and white label detection"""
    
    def __init__(self, database_instance):
        self.db = database_instance
        self.extractor = BrandExtractor()
        self._brand_analysis_cache = {}
        
    def find_consolidation_groups(self, brands_data: Dict[str, Dict]) -> Dict[str, List[str]]:
        """
        Find all consolidation groups from brands data
        Returns: {canonical_name: [list_of_brand_names]}
        """
        consolidation_groups = {}
        processed_brands = set()
        
        brand_names = list(brands_data.keys())
        
        # Sort by length to prioritize shorter names as canonical
        brand_names.sort(key=len)
        
        for brand_name in brand_names:
            if brand_name in processed_brands:
                continue
                
            # Find all brands that should be grouped with this one
            similar_brands = self._find_similar_brands(brand_name, brands_data, processed_brands)
            
            if len(similar_brands) > 1:
                canonical_name = self._select_canonical_name(similar_brands, brands_data)
                consolidation_groups[canonical_name] = similar_brands
                processed_brands.update(similar_brands)
        
        return consolidation_groups
    
    def _find_similar_brands(self, target_brand: str, all_brands: Dict, processed: Set[str]) -> List[str]:
        """Find all brands similar to the target brand"""
        similar_brands = [target_brand]
        target_analysis = self._get_brand_analysis(target_brand, all_brands[target_brand])
        
        for brand_name, brand_data in all_brands.items():
            if brand_name == target_brand or brand_name in processed:
                continue
                
            # Get analysis for this brand
            brand_analysis = self._get_brand_analysis(brand_name, brand_data)
            
            # Check if they should be consolidated
            should_consolidate, confidence, reason = self._should_consolidate_brands(
                target_brand, target_analysis,
                brand_name, brand_analysis
            )
            
            if should_consolidate and confidence >= 0.6:  # Minimum confidence threshold
                similar_brands.append(brand_name)
        
        return similar_brands
    
    def _get_brand_analysis(self, brand_name: str, brand_data: Dict) -> Dict:
        """Get or create brand analysis (cached)"""
        if brand_name not in self._brand_analysis_cache:
            self._brand_analysis_cache[brand_name] = self._analyze_brand(brand_name, brand_data)
        return self._brand_analysis_cache[brand_name]
    
    def _analyze_brand(self, brand_name: str, brand_data: Dict) -> Dict:
        """Analyze a brand for consolidation purposes"""
        analysis = {
            'brand_name': brand_name,
            'is_white_label': self._is_white_label_brand(brand_name),
            'core_brand': self.extractor.extract_core_brand(brand_name),
            'producers': [],
            'class_types': set(brand_data.get('class_types', [])),
            'countries': set(brand_data.get('countries', [])),
            'permit_numbers': brand_data.get('permit_numbers', [])
        }
        
        # Get producer information
        for permit in analysis['permit_numbers']:
            producer = self._find_producer_for_permit(permit)
            if producer:
                analysis['producers'].append({
                    'permit': permit,
                    'name': producer.get('owner_name', ''),
                    'operating_name': producer.get('operating_name', ''),
                    'type': producer.get('type', 'Unknown')
                })
        
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
    
    def _should_consolidate_brands(self, brand1_name: str, brand1_analysis: Dict, 
                                  brand2_name: str, brand2_analysis: Dict) -> Tuple[bool, float, str]:
        """
        Determine if two brands should be consolidated
        Returns: (should_consolidate, confidence, reason)
        """
        
        # Rule 1: White label protection - never consolidate different brand owners
        if self._different_brand_owners(brand1_analysis, brand2_analysis):
            return False, 0.1, "Different brand owners (white label protection)"
        
        # Rule 2: Same producer + similar core names = very high confidence
        if self._same_primary_producer(brand1_analysis, brand2_analysis):
            core_similarity = self._calculate_core_similarity(brand1_analysis['core_brand'], 
                                                            brand2_analysis['core_brand'])
            if core_similarity > 0.7:
                confidence = CONFIDENCE_RULES['same_producer_same_brand_owner']
                return True, confidence, f"Same producer + core similarity: {core_similarity:.2f}"
        
        # Rule 3: Same core brand name (high confidence)
        if brand1_analysis['core_brand'] and brand2_analysis['core_brand']:
            if brand1_analysis['core_brand'].upper() == brand2_analysis['core_brand'].upper():
                confidence = 0.90
                return True, confidence, f"Same core brand: {brand1_analysis['core_brand']}"
        
        # Rule 4: Brand family detection using extractor
        is_family, family_confidence, family_reason = self.extractor.is_likely_brand_family(
            brand1_name, brand2_name,
            self._get_primary_producer_name(brand1_analysis),
            self._get_primary_producer_name(brand2_analysis)
        )
        
        if is_family and family_confidence > 0.8:
            return True, family_confidence, family_reason
        
        # Rule 5: High name similarity with same class type
        name_similarity = self._calculate_name_similarity(brand1_name, brand2_name)
        if name_similarity > 0.85:
            # Boost confidence if same class types
            class_overlap = brand1_analysis['class_types'] & brand2_analysis['class_types']
            if class_overlap:
                confidence = min(name_similarity + 0.1, 1.0)
                return True, confidence, f"High name similarity + same class: {name_similarity:.2f}"
        
        return False, name_similarity, f"Low similarity: {name_similarity:.2f}"
    
    def _different_brand_owners(self, brand1_analysis: Dict, brand2_analysis: Dict) -> bool:
        """Check if brands have different owners (white label detection)"""
        brand1_white_label = brand1_analysis['is_white_label']
        brand2_white_label = brand2_analysis['is_white_label']
        
        # If one is white label and one isn't, they're different owners
        if brand1_white_label != brand2_white_label:
            return True
        
        # If both are white labels, check if same store brand
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
        
        # Check if both contain the same store brand
        for store_brand in WHITE_LABEL_BRANDS['retail_stores']:
            if store_brand in brand1_upper and store_brand in brand2_upper:
                return True
        
        return False
    
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
    
    def _same_primary_producer(self, brand1_analysis: Dict, brand2_analysis: Dict) -> bool:
        """Check if brands have the same primary producer"""
        producers1 = brand1_analysis.get('producers', [])
        producers2 = brand2_analysis.get('producers', [])
        
        if not producers1 or not producers2:
            return False
        
        # For now, just check if any producers match
        permits1 = {p['permit'] for p in producers1}
        permits2 = {p['permit'] for p in producers2}
        
        return bool(permits1 & permits2)
    
    def _get_primary_producer_name(self, brand_analysis: Dict) -> Optional[str]:
        """Get the primary producer name for a brand"""
        producers = brand_analysis.get('producers', [])
        if not producers:
            return None
        
        # Return first producer name (can be enhanced with primary/secondary logic later)
        return producers[0]['name']
    
    def _calculate_core_similarity(self, core1: str, core2: str) -> float:
        """Calculate similarity between core brand names"""
        if not core1 or not core2:
            return 0.0
        
        return SequenceMatcher(None, core1.upper(), core2.upper()).ratio()
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between full brand names"""
        similarity = SequenceMatcher(None, name1.upper(), name2.upper()).ratio()
        
        # Boost if one is substring of another
        if name1.upper() in name2.upper() or name2.upper() in name1.upper():
            similarity = max(similarity, 0.8)
        
        return similarity
    
    def _select_canonical_name(self, brand_list: List[str], brands_data: Dict) -> str:
        """Select the best canonical name for a brand family"""
        if not brand_list:
            return ""
        
        # Strategy 1: Prefer shortest name (usually the core brand)
        shortest = min(brand_list, key=len)
        
        # Strategy 2: Prefer most common core brand
        core_counts = {}
        for brand in brand_list:
            core = self.extractor.extract_core_brand(brand)
            if core:
                core_counts[core] = core_counts.get(core, 0) + 1
        
        if core_counts:
            most_common_core = max(core_counts.items(), key=lambda x: x[1])[0]
            
            # Find brand that matches the most common core
            for brand in brand_list:
                if self.extractor.extract_core_brand(brand).upper() == most_common_core.upper():
                    return brand
        
        # Fallback to shortest
        return shortest
    
    def get_consolidation_confidence(self, brand1_name: str, brand2_name: str, 
                                   brands_data: Dict) -> Tuple[float, str]:
        """Get consolidation confidence between two specific brands"""
        if brand1_name not in brands_data or brand2_name not in brands_data:
            return 0.0, "Brand not found in database"
        
        brand1_analysis = self._get_brand_analysis(brand1_name, brands_data[brand1_name])
        brand2_analysis = self._get_brand_analysis(brand2_name, brands_data[brand2_name])
        
        should_consolidate, confidence, reason = self._should_consolidate_brands(
            brand1_name, brand1_analysis, brand2_name, brand2_analysis
        )
        
        return confidence, reason
    
    def clear_cache(self):
        """Clear the brand analysis cache"""
        self._brand_analysis_cache.clear()