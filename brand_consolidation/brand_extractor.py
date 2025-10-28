"""
Brand Extractor - Advanced brand name extraction with producer context
Intelligently extracts core brand names from TTB registrations
"""

import re
from typing import List, Dict, Tuple, Optional
from .config import PRODUCT_TERMS, BRAND_PATTERNS

class BrandExtractor:
    """Extract core brand names from TTB registrations with producer awareness"""
    
    def __init__(self):
        self.product_terms_flat = self._flatten_product_terms()
        self.compiled_patterns = self._compile_patterns()
        
    def _flatten_product_terms(self) -> List[str]:
        """Flatten all product terms into a single list"""
        all_terms = []
        for category_terms in PRODUCT_TERMS.values():
            all_terms.extend(category_terms)
        return all_terms
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for efficiency"""
        compiled = {}
        for pattern_type, patterns in BRAND_PATTERNS.items():
            compiled[pattern_type] = [re.compile(pattern) for pattern in patterns]
        return compiled
    
    def extract_core_brand(self, brand_name: str, producer_name: str = None, class_type: str = None) -> str:
        """
        Extract core brand name with producer and category context
        
        Examples:
        "G4 ANEJO SINGLE BARREL RELEASE" → "G4"
        "MAKERS MARK CASK STRENGTH" → "Makers Mark" 
        "KIRKLAND SIGNATURE BOURBON" → "Kirkland Signature"
        """
        if not brand_name:
            return ""
        
        original_name = brand_name
        cleaned_name = brand_name.upper().strip()
        
        # Step 1: Handle special patterns first
        core_from_pattern = self._extract_from_patterns(cleaned_name)
        if core_from_pattern:
            cleaned_name = core_from_pattern
        
        # Step 2: Remove product terms based on category context
        cleaned_name = self._remove_product_terms(cleaned_name, class_type)
        
        # Step 3: Remove age statements and proof
        cleaned_name = self._remove_age_and_proof(cleaned_name)
        
        # Step 4: Clean up extra words and formatting
        cleaned_name = self._clean_final_name(cleaned_name)
        
        # Step 5: Validate result and apply producer context if needed
        final_name = self._validate_and_enhance(cleaned_name, original_name, producer_name)
        
        # Step 6: Apply proper case formatting
        return self._apply_proper_case(final_name)
    
    def _extract_from_patterns(self, brand_name: str) -> Optional[str]:
        """Extract brand using predefined patterns"""
        
        # Pattern 1: Possessive forms ("JACK'S PREMIUM" → "JACK")
        for pattern in self.compiled_patterns['possessive']:
            match = pattern.match(brand_name)
            if match:
                return match.group(1).strip()
        
        # Pattern 2: Company suffixes ("HEAVEN HILL DISTILLERY" → "HEAVEN HILL")
        for pattern_type in ['company', 'distillery', 'brewery', 'winery']:
            for pattern in self.compiled_patterns[pattern_type]:
                match = pattern.match(brand_name)
                if match:
                    return match.group(1).strip()
        
        # Pattern 3: Numbered products ("JACK DANIELS NO 7" → "JACK DANIELS")
        for pattern in self.compiled_patterns['numbered']:
            match = pattern.match(brand_name)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _remove_product_terms(self, brand_name: str, class_type: str = None) -> str:
        """Remove product-specific terms based on category"""
        words = brand_name.split()
        filtered_words = []
        
        # Determine which product terms to use based on class type
        relevant_terms = self._get_relevant_product_terms(class_type)
        
        for word in words:
            # Skip if word is a product term
            if word in relevant_terms:
                continue
            
            # Skip if word is a general product term
            if word in PRODUCT_TERMS['general']:
                continue
                
            filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def _get_relevant_product_terms(self, class_type: str = None) -> List[str]:
        """Get product terms relevant to the alcohol category"""
        relevant_terms = PRODUCT_TERMS['general'].copy()
        
        if not class_type:
            # If no class type, use all terms
            return self.product_terms_flat
        
        class_type_lower = class_type.lower()
        
        # Add category-specific terms
        for category in PRODUCT_TERMS.keys():
            if category in class_type_lower or class_type_lower in category:
                relevant_terms.extend(PRODUCT_TERMS[category])
                break
        
        # Always include size/volume terms
        relevant_terms.extend(PRODUCT_TERMS.get('size_volume', []))
        
        return relevant_terms
    
    def _remove_age_and_proof(self, brand_name: str) -> str:
        """Remove age statements and proof values"""
        # Remove age patterns (regex)
        for age_pattern in PRODUCT_TERMS.get('age_statements', []):
            brand_name = re.sub(age_pattern, '', brand_name, flags=re.IGNORECASE)
        
        # Remove proof patterns (regex) 
        for proof_pattern in PRODUCT_TERMS.get('proof_abv', []):
            brand_name = re.sub(proof_pattern, '', brand_name, flags=re.IGNORECASE)
        
        return brand_name.strip()
    
    def _clean_final_name(self, brand_name: str) -> str:
        """Final cleanup of the extracted name"""
        # Remove extra whitespace
        brand_name = re.sub(r'\s+', ' ', brand_name).strip()
        
        # Remove trailing punctuation and conjunctions
        brand_name = re.sub(r'\s*[-–—&]\s*$', '', brand_name).strip()
        
        # Remove leading/trailing articles
        brand_name = re.sub(r'^(?:THE|A|AN)\s+', '', brand_name, flags=re.IGNORECASE)
        brand_name = re.sub(r'\s+(?:THE|A|AN)$', '', brand_name, flags=re.IGNORECASE)
        
        return brand_name.strip()
    
    def _validate_and_enhance(self, extracted_name: str, original_name: str, producer_name: str = None) -> str:
        """Validate extraction result and enhance with producer context"""
        
        # If extraction resulted in empty or very short name, use original
        if not extracted_name or len(extracted_name) < 2:
            # Try to get first 1-3 words from original
            words = original_name.upper().split()
            return ' '.join(words[:3])
        
        # If result is too long, truncate intelligently
        if len(extracted_name.split()) > 4:
            words = extracted_name.split()
            return ' '.join(words[:3])
        
        # If we have producer context, check for brand-producer relationship
        if producer_name and extracted_name:
            enhanced_name = self._enhance_with_producer_context(extracted_name, producer_name)
            if enhanced_name:
                return enhanced_name
        
        return extracted_name
    
    def _enhance_with_producer_context(self, brand_name: str, producer_name: str) -> Optional[str]:
        """Enhance brand name using producer context"""
        if not producer_name:
            return None
        
        brand_words = set(brand_name.upper().split())
        producer_words = set(producer_name.upper().split())
        
        # If brand name is subset of producer name, it might be the core brand
        if brand_words.issubset(producer_words) and len(brand_words) >= 1:
            return brand_name
        
        # If producer name contains brand name, it's likely correct
        overlap = brand_words & producer_words
        if len(overlap) >= 1:
            return brand_name
        
        return None
    
    def _apply_proper_case(self, brand_name: str) -> str:
        """Apply proper case formatting to the final brand name"""
        if not brand_name:
            return ""
        
        words = []
        for word in brand_name.split():
            # Keep known acronyms uppercase
            if word.upper() in ['G4', 'XO', 'VS', 'VSOP', 'USA', 'UK', 'TTB', 'LLC', 'INC', 'CO']:
                words.append(word.upper())
            # Handle Roman numerals
            elif re.match(r'^[IVX]+$', word.upper()):
                words.append(word.upper())
            # Handle numbers
            elif word.isdigit():
                words.append(word)
            # Regular words - capitalize first letter
            else:
                words.append(word.capitalize())
        
        return ' '.join(words)
    
    def extract_brand_variations(self, brand_name: str) -> List[str]:
        """Generate possible variations of a brand name for matching"""
        variations = [brand_name]
        base_name = self.extract_core_brand(brand_name)
        
        if base_name and base_name != brand_name:
            variations.append(base_name)
        
        # Add common variations
        variations.extend([
            brand_name.upper(),
            brand_name.lower(),
            brand_name.title(),
            base_name.upper() if base_name else "",
            base_name.lower() if base_name else "",
        ])
        
        # Remove empty strings and duplicates
        variations = list(set([v for v in variations if v]))
        
        return variations
    
    def is_likely_brand_family(self, name1: str, name2: str, producer1: str = None, producer2: str = None) -> Tuple[bool, float, str]:
        """
        Determine if two names likely belong to the same brand family
        Returns (is_family, confidence, reason)
        """
        core1 = self.extract_core_brand(name1, producer1)
        core2 = self.extract_core_brand(name2, producer2)
        
        if not core1 or not core2:
            return False, 0.0, "Could not extract core brand names"
        
        # Exact core match
        if core1.upper() == core2.upper():
            return True, 0.95, f"Same core brand: {core1}"
        
        # One is substring of the other
        if core1.upper() in core2.upper() or core2.upper() in core1.upper():
            return True, 0.85, f"Substring match: {core1} / {core2}"
        
        # High similarity
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, core1.upper(), core2.upper()).ratio()
        
        if similarity > 0.8:
            return True, similarity, f"High similarity: {similarity:.2f}"
        
        # Same producer context boost
        if producer1 and producer2 and producer1.upper() == producer2.upper():
            if similarity > 0.6:
                return True, similarity + 0.2, f"Same producer + similarity: {similarity:.2f}"
        
        return False, similarity, f"Low similarity: {similarity:.2f}"