#!/usr/bin/env python3
"""
Agentic Brand Consolidation System
Self-learning system that improves brand matching accuracy through pattern recognition
and user feedback, learning from each CSV upload and consolidation decision
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

@dataclass
class ConsolidationPattern:
    """Represents a learned pattern for brand consolidation"""
    pattern_type: str  # 'suffix', 'prefix', 'variation', 'abbreviation', 'typo'
    base_pattern: str
    variation_pattern: str
    confidence: float
    success_count: int
    failure_count: int
    examples: List[Tuple[str, str]]  # List of (brand1, brand2) pairs
    learned_date: str
    last_updated: str

@dataclass
class ConsolidationFeedback:
    """User feedback on a consolidation decision"""
    timestamp: str
    brand_group: List[str]
    canonical_brand: str
    user_action: str  # 'approved', 'rejected', 'modified'
    confidence_predicted: float
    reason: Optional[str] = None
    modified_grouping: Optional[List[str]] = None

@dataclass
class BrandCharacteristics:
    """Characteristics of a brand for pattern learning"""
    has_year: bool
    has_location: bool
    has_product_type: bool
    word_count: int
    has_special_chars: bool
    has_numbers: bool
    alcohol_types: Set[str]
    countries: Set[str]
    producer_count: int

class AgenticConsolidationSystem:
    """
    Self-learning consolidation system that improves over time
    """
    
    def __init__(self, data_dir='data/consolidation_learning'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Learning data files
        self.patterns_file = os.path.join(data_dir, 'consolidation_patterns.json')
        self.feedback_file = os.path.join(data_dir, 'consolidation_feedback.json')
        self.knowledge_file = os.path.join(data_dir, 'consolidation_knowledge.json')
        self.upload_history_file = os.path.join(data_dir, 'upload_patterns.json')
        
        # Load existing learning data
        self.patterns = self._load_patterns()
        self.feedback_history = self._load_feedback()
        self.knowledge_base = self._load_knowledge()
        self.upload_patterns = self._load_upload_patterns()
        
        # Learning parameters
        self.min_confidence_threshold = 0.6
        self.pattern_learning_threshold = 3  # Min examples to learn pattern
        self.confidence_boost_per_success = 0.05
        self.confidence_penalty_per_failure = 0.1
        
        # Common variations and abbreviations
        self.common_variations = {
            'company': ['co', 'comp'],
            'corporation': ['corp'],
            'incorporated': ['inc'],
            'limited': ['ltd'],
            'distillery': ['dist', 'distilleries'],
            'brewery': ['brew', 'brewing', 'breweries'],
            'winery': ['wine', 'wines', 'vineyard', 'vineyards'],
            'spirits': ['spirit'],
            'whiskey': ['whisky'],
            'vodka': ['vodkas'],
            'and': ['&', 'n'],
        }
        
        # Initialize industry knowledge
        self._initialize_industry_knowledge()
    
    def _initialize_industry_knowledge(self):
        """Initialize with spirits industry knowledge"""
        if not self.knowledge_base:
            self.knowledge_base = {
                'brand_suffixes': {
                    'distillery': 0.9,
                    'distilleries': 0.9,
                    'brewery': 0.9,
                    'brewing': 0.9,
                    'winery': 0.9,
                    'vineyard': 0.9,
                    'spirits': 0.85,
                    'whiskey': 0.8,
                    'bourbon': 0.8,
                    'vodka': 0.8,
                    'gin': 0.8,
                    'rum': 0.8,
                    'tequila': 0.8,
                    'mezcal': 0.8,
                },
                'location_indicators': [
                    'california', 'kentucky', 'tennessee', 'texas', 'oregon',
                    'washington', 'new york', 'colorado', 'virginia'
                ],
                'year_pattern': r'\b(18|19|20)\d{2}\b',
                'batch_pattern': r'\b(batch|lot|barrel|cask)\s*#?\s*\d+\b',
                'special_edition_pattern': r'\b(limited|special|reserve|edition|select)\b',
            }
            self._save_knowledge()
    
    def learn_from_upload(self, brands_before: Dict, brands_after: Dict, filename: str):
        """
        Learn patterns from a new CSV upload
        Compares brands before and after to identify new variations
        """
        upload_event = {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'brands_added': len(brands_after) - len(brands_before),
            'patterns_discovered': []
        }
        
        # Find new brands that might be variations of existing ones
        new_brands = set(brands_after.keys()) - set(brands_before.keys())
        existing_brands = set(brands_before.keys())
        
        for new_brand in new_brands:
            # Check if this new brand is similar to any existing brand
            for existing_brand in existing_brands:
                similarity, pattern_type = self._analyze_brand_similarity(new_brand, existing_brand)
                
                if similarity >= 0.7:  # High similarity threshold
                    # Record this pattern
                    pattern = {
                        'new_brand': new_brand,
                        'existing_brand': existing_brand,
                        'similarity': similarity,
                        'pattern_type': pattern_type,
                        'auto_discovered': True
                    }
                    upload_event['patterns_discovered'].append(pattern)
                    
                    # Update our pattern knowledge
                    self._learn_pattern(existing_brand, new_brand, pattern_type, similarity)
        
        # Save upload history
        self.upload_patterns.append(upload_event)
        self._save_upload_patterns()
        
        return upload_event
    
    def _analyze_brand_similarity(self, brand1: str, brand2: str) -> Tuple[float, str]:
        """
        Analyze similarity between two brands and identify the pattern type
        Returns: (similarity_score, pattern_type)
        """
        brand1_lower = brand1.lower().strip()
        brand2_lower = brand2.lower().strip()
        
        # Direct match
        if brand1_lower == brand2_lower:
            return 1.0, 'exact'
        
        # Check for year variations (e.g., "Brand 2023" vs "Brand 2024")
        if self._is_year_variation(brand1_lower, brand2_lower):
            return 0.95, 'year_variation'
        
        # Check for location variations (e.g., "Brand California" vs "Brand Kentucky")
        if self._is_location_variation(brand1_lower, brand2_lower):
            return 0.9, 'location_variation'
        
        # Check for suffix/prefix variations
        if self._is_suffix_variation(brand1_lower, brand2_lower):
            return 0.85, 'suffix_variation'
        
        # Check for abbreviations
        if self._is_abbreviation(brand1_lower, brand2_lower):
            return 0.8, 'abbreviation'
        
        # Check for special edition variations
        if self._is_special_edition(brand1_lower, brand2_lower):
            return 0.85, 'special_edition'
        
        # Use sequence matching for general similarity
        matcher = SequenceMatcher(None, brand1_lower, brand2_lower)
        base_similarity = matcher.ratio()
        
        # Apply learned pattern boosts
        pattern_boost = self._get_pattern_confidence_boost(brand1, brand2)
        
        final_similarity = min(base_similarity + pattern_boost, 1.0)
        
        if final_similarity >= 0.7:
            return final_similarity, 'fuzzy_match'
        
        return final_similarity, 'no_match'
    
    def _is_year_variation(self, brand1: str, brand2: str) -> bool:
        """Check if brands differ only by year"""
        year_pattern = self.knowledge_base.get('year_pattern', r'\b(18|19|20)\d{2}\b')
        
        # Remove years from both brands
        brand1_no_year = re.sub(year_pattern, '', brand1).strip()
        brand2_no_year = re.sub(year_pattern, '', brand2).strip()
        
        # Check if base brands match
        if brand1_no_year == brand2_no_year and brand1_no_year:
            # Verify both had years
            years1 = re.findall(year_pattern, brand1)
            years2 = re.findall(year_pattern, brand2)
            return bool(years1) and bool(years2)
        
        return False
    
    def _is_location_variation(self, brand1: str, brand2: str) -> bool:
        """Check if brands differ only by location"""
        locations = self.knowledge_base.get('location_indicators', [])
        
        for location in locations:
            brand1_no_loc = brand1.replace(location, '').strip()
            brand2_no_loc = brand2.replace(location, '').strip()
            
            if brand1_no_loc == brand2_no_loc and brand1_no_loc:
                return True
        
        return False
    
    def _is_suffix_variation(self, brand1: str, brand2: str) -> bool:
        """Check if brands differ by known suffixes"""
        suffixes = self.knowledge_base.get('brand_suffixes', {})
        
        for suffix in suffixes:
            if brand1.endswith(suffix) and not brand2.endswith(suffix):
                if brand1.replace(suffix, '').strip() == brand2:
                    return True
            elif brand2.endswith(suffix) and not brand1.endswith(suffix):
                if brand2.replace(suffix, '').strip() == brand1:
                    return True
        
        return False
    
    def _is_abbreviation(self, brand1: str, brand2: str) -> bool:
        """Check if one brand is an abbreviation of the other"""
        for full_word, abbreviations in self.common_variations.items():
            for abbrev in abbreviations:
                if full_word in brand1 and abbrev in brand2:
                    test1 = brand1.replace(full_word, abbrev)
                    if test1 == brand2:
                        return True
                elif full_word in brand2 and abbrev in brand1:
                    test2 = brand2.replace(full_word, abbrev)
                    if test2 == brand1:
                        return True
        
        return False
    
    def _is_special_edition(self, brand1: str, brand2: str) -> bool:
        """Check if brands differ by special edition markers"""
        special_pattern = self.knowledge_base.get('special_edition_pattern', 
                                                 r'\b(limited|special|reserve|edition|select)\b')
        
        # Remove special edition markers
        brand1_base = re.sub(special_pattern, '', brand1).strip()
        brand2_base = re.sub(special_pattern, '', brand2).strip()
        
        # Normalize multiple spaces
        brand1_base = ' '.join(brand1_base.split())
        brand2_base = ' '.join(brand2_base.split())
        
        return brand1_base == brand2_base and brand1_base
    
    def _get_pattern_confidence_boost(self, brand1: str, brand2: str) -> float:
        """Get confidence boost from learned patterns"""
        boost = 0.0
        
        for pattern in self.patterns:
            if self._pattern_matches(brand1, brand2, pattern):
                # Weight by pattern confidence and success rate
                success_rate = pattern['success_count'] / max(
                    pattern['success_count'] + pattern['failure_count'], 1
                )
                boost += pattern['confidence'] * success_rate * 0.1
        
        return min(boost, 0.3)  # Cap at 30% boost
    
    def _pattern_matches(self, brand1: str, brand2: str, pattern: Dict) -> bool:
        """Check if a brand pair matches a learned pattern"""
        # Simple pattern matching without recursive analysis
        pattern_type = pattern.get('pattern_type', '')
        base = pattern.get('base_pattern', '').lower()
        
        brand1_lower = brand1.lower().strip()
        brand2_lower = brand2.lower().strip()
        
        # Check if the base pattern is present
        if base and base not in brand1_lower and base not in brand2_lower:
            return False
        
        # Simple pattern type checks without recursion
        if pattern_type == 'year_variation':
            return self._is_year_variation(brand1_lower, brand2_lower)
        elif pattern_type == 'location_variation':
            return self._is_location_variation(brand1_lower, brand2_lower)
        elif pattern_type == 'suffix_variation':
            return self._is_suffix_variation(brand1_lower, brand2_lower)
        elif pattern_type == 'abbreviation':
            return self._is_abbreviation(brand1_lower, brand2_lower)
        elif pattern_type == 'special_edition':
            return self._is_special_edition(brand1_lower, brand2_lower)
        
        return True
    
    def _learn_pattern(self, brand1: str, brand2: str, pattern_type: str, confidence: float):
        """Learn a new consolidation pattern"""
        # Find common substring
        matcher = SequenceMatcher(None, brand1.lower(), brand2.lower())
        match = matcher.find_longest_match(0, len(brand1), 0, len(brand2))
        base_pattern = brand1[match.a:match.a + match.size] if match.size > 3 else ""
        
        # Check if pattern exists
        existing_pattern = None
        for pattern in self.patterns:
            if (pattern['pattern_type'] == pattern_type and 
                pattern['base_pattern'] == base_pattern):
                existing_pattern = pattern
                break
        
        if existing_pattern:
            # Update existing pattern
            existing_pattern['examples'].append((brand1, brand2))
            existing_pattern['success_count'] += 1
            existing_pattern['confidence'] = min(
                existing_pattern['confidence'] + self.confidence_boost_per_success, 1.0
            )
            existing_pattern['last_updated'] = datetime.now().isoformat()
        else:
            # Create new pattern
            new_pattern = {
                'pattern_type': pattern_type,
                'base_pattern': base_pattern,
                'variation_pattern': f"{brand1} <-> {brand2}",
                'confidence': confidence,
                'success_count': 1,
                'failure_count': 0,
                'examples': [(brand1, brand2)],
                'learned_date': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            self.patterns.append(new_pattern)
        
        self._save_patterns()
    
    def predict_consolidation_groups(self, brands: Dict[str, Dict]) -> Dict[str, List[str]]:
        """
        Predict consolidation groups using learned patterns
        Returns: {canonical_brand: [brand_variations]}
        """
        groups = {}
        processed = set()
        
        # Sort brands by length (prefer shorter as canonical)
        sorted_brands = sorted(brands.keys(), key=len)
        
        for brand in sorted_brands:
            if brand in processed:
                continue
            
            # Start a new group
            group = [brand]
            processed.add(brand)
            
            # Find similar brands
            for other_brand in sorted_brands:
                if other_brand in processed:
                    continue
                
                similarity, pattern_type = self._analyze_brand_similarity(brand, other_brand)
                
                # Apply learned confidence adjustments
                adjusted_confidence = self._adjust_confidence_from_feedback(
                    brand, other_brand, similarity
                )
                
                if adjusted_confidence >= self.min_confidence_threshold:
                    group.append(other_brand)
                    processed.add(other_brand)
            
            if len(group) > 1:
                # Select best canonical name
                canonical = self._select_canonical_name(group, brands)
                groups[canonical] = group
        
        return groups
    
    def _select_canonical_name(self, group: List[str], brands: Dict) -> str:
        """Select the best canonical name for a brand group"""
        scores = {}
        
        for brand in group:
            score = 0
            
            # Prefer shorter names
            score += (50 - len(brand)) * 0.5
            
            # Prefer names without years
            if not re.search(r'\b(18|19|20)\d{2}\b', brand):
                score += 10
            
            # Prefer names without special editions
            if not re.search(r'\b(limited|special|reserve|edition|select)\b', brand.lower()):
                score += 10
            
            # Prefer names with more SKUs
            brand_data = brands.get(brand, {})
            score += len(brand_data.get('skus', [])) * 2
            
            # Prefer verified websites
            if brand_data.get('enrichment', {}).get('website', {}).get('verification_status') == 'verified':
                score += 20
            
            scores[brand] = score
        
        # Return brand with highest score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _adjust_confidence_from_feedback(self, brand1: str, brand2: str, base_confidence: float) -> float:
        """Adjust confidence based on historical feedback"""
        adjustment = 0.0
        
        # Check feedback history for similar consolidations
        for feedback in self.feedback_history:
            if self._is_similar_consolidation(brand1, brand2, feedback['brand_group']):
                if feedback['user_action'] == 'approved':
                    adjustment += 0.1
                elif feedback['user_action'] == 'rejected':
                    adjustment -= 0.2
        
        return max(0.0, min(1.0, base_confidence + adjustment))
    
    def _is_similar_consolidation(self, brand1: str, brand2: str, group: List[str]) -> bool:
        """Check if a consolidation is similar to a previous one"""
        # Check if both brands share characteristics with the group
        for brand in group:
            sim1, _ = self._analyze_brand_similarity(brand1, brand)
            sim2, _ = self._analyze_brand_similarity(brand2, brand)
            if sim1 > 0.7 or sim2 > 0.7:
                return True
        return False
    
    def record_user_feedback(self, brand_group: List[str], canonical: str, 
                            action: str, confidence: float, reason: str = None):
        """Record user feedback on a consolidation decision"""
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'brand_group': brand_group,
            'canonical_brand': canonical,
            'user_action': action,
            'confidence_predicted': confidence,
            'reason': reason
        }
        
        self.feedback_history.append(feedback)
        self._save_feedback()
        
        # Update patterns based on feedback
        if action == 'approved':
            self._reinforce_patterns(brand_group)
        elif action == 'rejected':
            self._penalize_patterns(brand_group)
    
    def _reinforce_patterns(self, brand_group: List[str]):
        """Reinforce patterns that led to approved consolidation"""
        for i, brand1 in enumerate(brand_group):
            for brand2 in brand_group[i+1:]:
                _, pattern_type = self._analyze_brand_similarity(brand1, brand2)
                self._learn_pattern(brand1, brand2, pattern_type, 0.9)
    
    def _penalize_patterns(self, brand_group: List[str]):
        """Penalize patterns that led to rejected consolidation"""
        for pattern in self.patterns:
            for brand1 in brand_group:
                for brand2 in brand_group:
                    if brand1 != brand2 and self._pattern_matches(brand1, brand2, pattern):
                        pattern['failure_count'] += 1
                        pattern['confidence'] = max(
                            pattern['confidence'] - self.confidence_penalty_per_failure, 0.1
                        )
        self._save_patterns()
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about the learning system"""
        total_patterns = len(self.patterns)
        high_confidence_patterns = len([p for p in self.patterns if p['confidence'] > 0.8])
        
        pattern_types = Counter(p['pattern_type'] for p in self.patterns)
        
        total_feedback = len(self.feedback_history)
        approved = len([f for f in self.feedback_history if f['user_action'] == 'approved'])
        
        return {
            'total_patterns_learned': total_patterns,
            'high_confidence_patterns': high_confidence_patterns,
            'pattern_types': dict(pattern_types),
            'total_feedback_events': total_feedback,
            'approval_rate': approved / max(total_feedback, 1),
            'uploads_processed': len(self.upload_patterns),
            'last_learning_event': self.feedback_history[-1]['timestamp'] if self.feedback_history else None
        }
    
    # Data persistence methods
    def _load_patterns(self) -> List[Dict]:
        """Load consolidation patterns"""
        try:
            with open(self.patterns_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _save_patterns(self):
        """Save consolidation patterns"""
        with open(self.patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    def _load_feedback(self) -> List[Dict]:
        """Load feedback history"""
        try:
            with open(self.feedback_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _save_feedback(self):
        """Save feedback history"""
        with open(self.feedback_file, 'w') as f:
            json.dump(self.feedback_history, f, indent=2)
    
    def _load_knowledge(self) -> Dict:
        """Load knowledge base"""
        try:
            with open(self.knowledge_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_knowledge(self):
        """Save knowledge base"""
        with open(self.knowledge_file, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2)
    
    def _load_upload_patterns(self) -> List[Dict]:
        """Load upload pattern history"""
        try:
            with open(self.upload_history_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _save_upload_patterns(self):
        """Save upload pattern history"""
        with open(self.upload_history_file, 'w') as f:
            json.dump(self.upload_patterns, f, indent=2)