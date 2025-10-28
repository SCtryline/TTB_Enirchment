#!/usr/bin/env python3
"""
Agentic Learning System for Brand Enrichment
Continuously improves accuracy through user feedback and pattern recognition
"""

import json
import os
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import pickle
import numpy as np
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class LearningEvent:
    """Represents a learning event from user feedback or system observation"""
    timestamp: str
    event_type: str  # 'verification', 'rejection', 'flag', 'pattern_discovery', 'search_strategy'
    brand_name: str
    domain: str
    confidence_predicted: float
    user_action: str  # 'verified', 'rejected', 'flagged', 'successful_search'
    features: Dict[str, Any]  # Features that led to the prediction
    metadata: Dict[str, Any] = None

@dataclass
class DomainPattern:
    """Represents a learned pattern for domain matching"""
    pattern: str
    pattern_type: str  # 'exact_match', 'substring', 'regex', 'industry_keyword'
    success_rate: float
    confidence_boost: float
    sample_count: int
    last_updated: str

@dataclass
class SearchStrategyPattern:
    """Represents a learned search strategy pattern"""
    strategy_name: str  # 'simple_unquoted', 'quoted_plus_winery', 'quoted_plus_distillery', etc.
    brand_characteristics: Dict[str, Any]  # Features that identify when to use this strategy
    success_rate: float
    average_confidence: float
    sample_count: int
    examples: List[str]  # Example brand names where this worked
    last_updated: str = ""

@dataclass  
class RelevancePattern:
    """Represents learned patterns for URL relevance criteria"""
    term: str  # The term that indicates relevance (e.g., 'gin', 'craft spirits', 'microbrewery')
    term_type: str  # 'product', 'facility', 'descriptor', 'industry_term'
    contexts: List[str]  # Contexts where this term was found (title, snippet, domain)
    success_rate: float  # How often URLs with this term were verified
    sample_count: int
    brand_examples: List[str]  # Example brands where this term was relevant
    last_updated: str

class AgenticLearningSystem:
    """
    Agentic learning system that improves brand enrichment accuracy over time
    """
    
    def __init__(self, data_dir='data/learning'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Learning data files
        self.events_file = os.path.join(data_dir, 'learning_events.json')
        self.patterns_file = os.path.join(data_dir, 'domain_patterns.json')
        self.knowledge_file = os.path.join(data_dir, 'knowledge_base.json')
        self.model_file = os.path.join(data_dir, 'confidence_model.pkl')
        self.strategy_patterns_file = os.path.join(data_dir, 'search_strategy_patterns.json')
        self.relevance_patterns_file = os.path.join(data_dir, 'relevance_patterns.json')
        
        # Load existing data
        self.learning_events = self._load_learning_events()
        self.domain_patterns = self._load_domain_patterns()
        self.knowledge_base = self._load_knowledge_base()
        self.strategy_patterns = self._load_strategy_patterns()
        self.relevance_patterns = self._load_relevance_patterns()
        
        # Learning parameters
        self.min_samples_for_pattern = 3
        self.confidence_update_threshold = 0.1
        self.pattern_confidence_threshold = 0.7
        
        # Initialize with spirits industry knowledge
        self._initialize_industry_knowledge()
    
    def record_user_feedback(self, brand_name: str, domain: str, 
                           predicted_confidence: float, user_action: str,
                           features: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Record user feedback for learning"""
        event = LearningEvent(
            timestamp=datetime.now().isoformat(),
            event_type='user_feedback',
            brand_name=brand_name,
            domain=domain,
            confidence_predicted=predicted_confidence,
            user_action=user_action,
            features=features,
            metadata=metadata or {}
        )
        
        self.learning_events.append(event)
        self._save_learning_events()
        
        # Trigger learning from this feedback
        self._learn_from_feedback(event)
        
        logger.info(f"Recorded user feedback: {brand_name} -> {domain} ({user_action})")
    
    def _learn_from_feedback(self, event: LearningEvent):
        """Learn from user feedback to improve future predictions"""
        
        # Update domain patterns
        self._update_domain_patterns(event)
        
        # Update confidence calibration  
        self._update_confidence_calibration(event)
        
        # Discover new patterns
        self._discover_patterns(event)
        
        # Update knowledge base
        self._update_knowledge_base(event)
    
    def _update_domain_patterns(self, event: LearningEvent):
        """Update domain matching patterns based on feedback"""
        brand_lower = event.brand_name.lower().replace(' ', '')
        domain_lower = event.domain.lower()
        
        # Extract potential patterns
        patterns_to_update = []
        
        # Exact brand name match
        if brand_lower in domain_lower:
            patterns_to_update.append(('exact_brand_match', brand_lower))
        
        # Brand words in domain
        brand_words = event.brand_name.lower().split()
        for word in brand_words:
            if len(word) > 3 and word in domain_lower:
                patterns_to_update.append(('brand_word_match', word))
        
        # Industry keywords
        industry_keywords = self.knowledge_base.get('industry_keywords', [])
        for keyword in industry_keywords:
            if keyword in domain_lower:
                patterns_to_update.append(('industry_keyword', keyword))
        
        # Update pattern success rates
        for pattern_type, pattern in patterns_to_update:
            pattern_key = f"{pattern_type}:{pattern}"
            
            if pattern_key not in self.domain_patterns:
                self.domain_patterns[pattern_key] = DomainPattern(
                    pattern=pattern,
                    pattern_type=pattern_type,
                    success_rate=0.0,
                    confidence_boost=0.0,
                    sample_count=0,
                    last_updated=datetime.now().isoformat()
                )
            
            dp = self.domain_patterns[pattern_key]
            
            # Update success rate based on user action
            success = 1.0 if event.user_action == 'verified' else 0.0
            dp.success_rate = (dp.success_rate * dp.sample_count + success) / (dp.sample_count + 1)
            dp.sample_count += 1
            dp.last_updated = datetime.now().isoformat()
            
            # Calculate confidence boost based on success rate
            if dp.sample_count >= self.min_samples_for_pattern:
                dp.confidence_boost = max(0.0, (dp.success_rate - 0.5) * 0.4)
        
        self._save_domain_patterns()
    
    def learn_from_verified_url(self, brand_name: str, url: str, title: str, snippet: str, brand_context: Dict = None):
        """Learn relevance patterns from verified URLs and manual inputs"""
        logger.info(f"🧠 Learning relevance patterns from verified URL: {brand_name} → {url}")
        self._learn_from_url_feedback(brand_name, url, title, snippet, brand_context, verified=True)
    
    def learn_from_rejected_url(self, brand_name: str, url: str, title: str, snippet: str, brand_context: Dict = None, rejection_reason: str = None):
        """Learn what NOT to suggest from rejected URLs"""
        logger.info(f"🚫 Learning from rejected URL: {brand_name} → {url} (reason: {rejection_reason})")
        self._learn_from_url_feedback(brand_name, url, title, snippet, brand_context, verified=False, rejection_reason=rejection_reason)
    
    def _learn_from_url_feedback(self, brand_name: str, url: str, title: str, snippet: str, brand_context: Dict = None, verified: bool = True, rejection_reason: str = None):
        """Learn from both verified and rejected URL feedback"""
        # Extract text content for analysis
        combined_text = f"{url} {title} {snippet}".lower()
        
        # Extract terms that appear in this URL
        terms = self._extract_relevance_terms(combined_text, brand_name, brand_context)
        
        for term_info in terms:
            term = term_info['term']
            term_type = term_info['type']
            context = term_info['context']
            
            # Create or update relevance pattern
            pattern_key = f"{term_type}:{term}"
            
            if pattern_key in self.relevance_patterns:
                # Update existing pattern
                pattern = self.relevance_patterns[pattern_key]
                pattern.sample_count += 1
                
                if verified:
                    # Positive feedback - increase success rate
                    pattern.success_rate = (pattern.success_rate * (pattern.sample_count - 1) + 1.0) / pattern.sample_count
                    pattern.contexts = list(set(pattern.contexts + [context]))
                    pattern.brand_examples = list(set(pattern.brand_examples + [brand_name]))
                    logger.info(f"✅ Reinforced relevance term: '{term}' ({term_type}) - now {pattern.success_rate:.2%} success")
                else:
                    # Negative feedback - decrease success rate
                    pattern.success_rate = (pattern.success_rate * (pattern.sample_count - 1) + 0.0) / pattern.sample_count
                    logger.info(f"❌ Weakened relevance term: '{term}' ({term_type}) - now {pattern.success_rate:.2%} success")
                
                pattern.last_updated = datetime.now().isoformat()
            else:
                # Create new pattern
                initial_success_rate = 1.0 if verified else 0.0
                self.relevance_patterns[pattern_key] = RelevancePattern(
                    term=term,
                    term_type=term_type,
                    contexts=[context],
                    success_rate=initial_success_rate,
                    sample_count=1,
                    brand_examples=[brand_name] if verified else [],
                    last_updated=datetime.now().isoformat()
                )
                
                if verified:
                    logger.info(f"✅ Learned new relevance term: '{term}' ({term_type})")
                else:
                    logger.info(f"❌ Learned problematic term: '{term}' ({term_type}) - will reduce relevance")
        
        # Learn from rejection patterns - identify terms that lead to false positives
        if not verified and rejection_reason:
            self._learn_rejection_patterns(combined_text, brand_name, rejection_reason)
        
        # Save updated patterns
        self._save_relevance_patterns()
    
    def _learn_rejection_patterns(self, combined_text: str, brand_name: str, rejection_reason: str):
        """Learn from rejection reasons to identify false positive patterns"""
        
        # Common rejection patterns to learn from
        rejection_patterns = {
            'wrong_industry': [
                r'\b(restaurant|hotel|bar|pub|club)\b',  # Hospitality vs production
                r'\b(review|rating|blog|news)\b',        # Information sites
                r'\b(job|career|hiring|employment)\b'    # Job sites
            ],
            'wrong_company': [
                r'\b(consulting|marketing|design|software)\b',  # Non-alcohol businesses
                r'\b(real estate|finance|insurance)\b'          # Other industries
            ],
            'social_media': [
                r'\b(facebook|instagram|twitter|linkedin|social)\b'
            ]
        }
        
        # Extract potentially problematic terms based on rejection reason
        for pattern_type, patterns in rejection_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    term = match.group(1).lower()
                    
                    # Create negative pattern
                    pattern_key = f"negative_indicator:{term}"
                    
                    if pattern_key in self.relevance_patterns:
                        pattern = self.relevance_patterns[pattern_key]
                        pattern.sample_count += 1
                        pattern.success_rate = (pattern.success_rate * (pattern.sample_count - 1) + 0.0) / pattern.sample_count
                    else:
                        self.relevance_patterns[pattern_key] = RelevancePattern(
                            term=term,
                            term_type='negative_indicator',
                            contexts=['rejection'],
                            success_rate=0.0,
                            sample_count=1,
                            brand_examples=[],
                            last_updated=datetime.now().isoformat()
                        )
                        
                    logger.info(f"🚫 Learned negative indicator: '{term}' (reason: {rejection_reason})")
    
    def _extract_relevance_terms(self, combined_text: str, brand_name: str, brand_context: Dict = None) -> List[Dict]:
        """Extract new relevance terms from verified URL content"""
        new_terms = []
        
        # Known alcohol products (baseline)
        known_products = {
            'whiskey', 'whisky', 'bourbon', 'scotch', 'rye', 'tennessee whiskey',
            'irish whiskey', 'irish whisky', 'vodka', 'gin', 'rum', 'tequila', 
            'mezcal', 'brandy', 'cognac', 'wine', 'beer', 'ale', 'lager', 
            'stout', 'ipa', 'spirits', 'liquor', 'liqueur'
        }
        
        known_facilities = {
            'distillery', 'distilleries', 'distilling', 'distiller',
            'brewery', 'breweries', 'brewing', 'brewer', 'brewhouse',
            'winery', 'wineries', 'winemaker', 'vineyard', 'vintner'
        }
        
        # Extract potential new product terms
        product_patterns = [
            r'\b(\w+)\s+(?:spirits?|liquor|alcohol)\b',  # "craft spirits", "premium liquor"
            r'\b(?:artisan|craft|premium|small batch|handcrafted)\s+(\w+)\b',  # "craft gin", "artisan whiskey"
            r'\b(\w+)(?:ed|ing)?\s+(?:in|with|from)\s+(?:barrels?|casks?|oak)\b',  # "aged in barrels"
            r'\b(?:single|double|triple)\s+(\w+)\b',  # "single malt", "triple distilled"
            r'\b(\w+)\s+(?:variety|style|blend)\b',  # "bourbon variety", "wine style"
        ]
        
        for pattern in product_patterns:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                term = match.group(1).lower()
                if len(term) > 2 and term not in known_products and term not in known_facilities:
                    new_terms.append({
                        'term': term,
                        'type': 'product_descriptor',
                        'context': 'snippet'
                    })
        
        # Extract facility-related terms
        facility_patterns = [
            r'\b(\w+house)\b',  # "brewhouse", "malthouse", "taphouse"
            r'\b(\w+)\s+(?:facility|operation|company)\b',  # "brewing facility", "distilling operation"
            r'\b(?:the\s+)?(\w+)\s+(?:estate|manor|farm)\b',  # "estate", "farm"
        ]
        
        for pattern in facility_patterns:
            matches = re.finditer(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                term = match.group(1).lower()
                if len(term) > 2 and term not in known_facilities:
                    new_terms.append({
                        'term': term,
                        'type': 'facility_type',
                        'context': 'snippet'
                    })
        
        # Extract industry-specific descriptors from brand context
        if brand_context and brand_context.get('class_types'):
            for class_type in brand_context['class_types']:
                # Extract descriptive terms from class types
                class_lower = class_type.lower()
                
                # Split and analyze class type terms
                for term in class_lower.split():
                    if len(term) > 3 and term not in known_products:
                        new_terms.append({
                            'term': term,
                            'type': 'product_type',
                            'context': 'brand_context'
                        })
        
        return new_terms
    
    def get_learned_relevance_terms(self) -> Dict[str, List[str]]:
        """Get learned relevance terms for use in URL scoring (only high-success terms)"""
        learned_terms = {
            'products': [],
            'facilities': [],
            'descriptors': [],
            'negative_indicators': []
        }
        
        for pattern in self.relevance_patterns.values():
            if pattern.term_type == 'negative_indicator':
                # Include negative indicators that have been consistently rejected
                if pattern.success_rate <= 0.3 and pattern.sample_count >= 2:
                    learned_terms['negative_indicators'].append(pattern.term)
            else:
                # Only include positive terms with high success rate
                if pattern.success_rate >= 0.7 and pattern.sample_count >= 2:
                    if pattern.term_type == 'product_type':
                        learned_terms['products'].append(pattern.term)
                    elif pattern.term_type == 'facility_type':
                        learned_terms['facilities'].append(pattern.term)
                    elif pattern.term_type == 'product_descriptor':
                        learned_terms['descriptors'].append(pattern.term)
        
        return learned_terms
    
    def _update_confidence_calibration(self, event: LearningEvent):
        """Update confidence calibration based on user feedback"""
        # This will be used by _get_calibration_factor to improve confidence predictions
        # For now, the learning events stored are sufficient for calibration
        # Future enhancement: Could implement more sophisticated calibration models
        pass
    
    def _discover_patterns(self, event: LearningEvent):
        """Discover new patterns from successful verifications"""
        if event.user_action != 'verified':
            return
        
        brand_name = event.brand_name
        domain = event.domain
        
        # Look for novel patterns in successful matches
        patterns = []
        
        # Character-level patterns
        brand_chars = set(brand_name.lower().replace(' ', ''))
        domain_chars = set(domain.lower().replace('.', '').replace('-', ''))
        char_overlap = len(brand_chars & domain_chars) / max(len(brand_chars), 1)
        
        if char_overlap > 0.6:
            patterns.append(('high_char_overlap', f"overlap_{int(char_overlap*100)}"))
        
        # Numeric patterns (like "1220 SPIRITS" -> "1220spirits.com")
        brand_numbers = re.findall(r'\d+', brand_name)
        domain_numbers = re.findall(r'\d+', domain)
        
        if brand_numbers and brand_numbers == domain_numbers:
            patterns.append(('numeric_match', brand_numbers[0]))
        
        # Add discovered patterns to knowledge base
        for pattern_type, pattern in patterns:
            self._add_discovered_pattern(pattern_type, pattern, event)
    
    def get_enhanced_confidence(self, brand_name: str, domain: str, 
                              base_confidence: float, features: Dict[str, Any]) -> float:
        """Get enhanced confidence using learned patterns"""
        
        enhanced_confidence = base_confidence
        adjustments = []
        
        brand_lower = brand_name.lower().replace(' ', '')
        domain_lower = domain.lower()
        
        # Apply learned domain patterns
        for pattern_key, dp in self.domain_patterns.items():
            if dp.sample_count < self.min_samples_for_pattern:
                continue
                
            pattern_type, pattern = pattern_key.split(':', 1)
            pattern_matches = False
            
            if pattern_type == 'exact_brand_match' and pattern in domain_lower:
                pattern_matches = True
            elif pattern_type == 'brand_word_match' and pattern in domain_lower:
                pattern_matches = True
            elif pattern_type == 'industry_keyword' and pattern in domain_lower:
                pattern_matches = True
            
            if pattern_matches:
                adjustment = dp.confidence_boost
                enhanced_confidence = min(1.0, enhanced_confidence + adjustment)
                adjustments.append(f"{pattern_type}:+{adjustment:.2f}")
        
        # Apply historical calibration
        calibration_factor = self._get_calibration_factor(base_confidence)
        enhanced_confidence = enhanced_confidence * calibration_factor
        
        if adjustments:
            logger.debug(f"Confidence enhanced for {brand_name} -> {domain}: "
                        f"{base_confidence:.2f} -> {enhanced_confidence:.2f} "
                        f"({', '.join(adjustments)})")
        
        return enhanced_confidence
    
    def _get_calibration_factor(self, predicted_confidence: float) -> float:
        """Get calibration factor based on historical accuracy"""
        
        # Group events by confidence ranges
        confidence_ranges = [
            (0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)
        ]
        
        for min_conf, max_conf in confidence_ranges:
            if min_conf <= predicted_confidence < max_conf:
                # Calculate actual success rate in this range
                range_events = [
                    e for e in self.learning_events
                    if min_conf <= e.confidence_predicted < max_conf
                    and e.event_type == 'user_feedback'
                ]
                
                if len(range_events) >= 5:  # Minimum samples for calibration
                    actual_success_rate = sum(
                        1 for e in range_events if e.user_action == 'verified'
                    ) / len(range_events)
                    
                    expected_confidence = (min_conf + max_conf) / 2
                    calibration_factor = actual_success_rate / max(expected_confidence, 0.1)
                    
                    return min(1.5, max(0.5, calibration_factor))  # Bound the adjustment
        
        return 1.0  # No calibration if insufficient data
    
    def suggest_search_improvements(self, brand_name: str) -> List[str]:
        """Suggest improved search queries based on learned patterns"""
        suggestions = []
        
        # Base suggestions
        suggestions.append(f'"{brand_name}"')  # Exact match
        
        # Add industry context based on learned patterns
        industry_terms = self.knowledge_base.get('effective_search_terms', [])
        for term in industry_terms[:3]:  # Top 3 most effective
            suggestions.append(f'"{brand_name}" {term}')
        
        # Add learned brand-specific patterns
        brand_patterns = self._get_brand_specific_patterns(brand_name)
        for pattern in brand_patterns:
            suggestions.append(f'"{brand_name}" {pattern}')
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _get_brand_specific_patterns(self, brand_name: str) -> List[str]:
        """Get patterns specific to this brand type"""
        patterns = []
        
        # Analyze brand name characteristics
        has_numbers = bool(re.search(r'\d', brand_name))
        word_count = len(brand_name.split())
        
        if has_numbers:
            patterns.append('official website')
        
        if word_count > 1:
            patterns.append('distillery')
            patterns.append('spirits')
        
        return patterns
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about what the system has learned"""
        
        total_events = len(self.learning_events)
        verified_events = sum(1 for e in self.learning_events if e.user_action == 'verified')
        rejected_events = sum(1 for e in self.learning_events if e.user_action == 'rejected')
        
        # Top patterns by success rate
        top_patterns = sorted(
            [(k, v) for k, v in self.domain_patterns.items() 
             if v.sample_count >= self.min_samples_for_pattern],
            key=lambda x: x[1].success_rate,
            reverse=True
        )[:10]
        
        # Recent learning trends
        recent_events = [
            e for e in self.learning_events 
            if datetime.fromisoformat(e.timestamp) > datetime.now() - timedelta(days=7)
        ]
        
        return {
            'total_learning_events': total_events,
            'verified_websites': verified_events,
            'rejected_websites': rejected_events,
            'success_rate': verified_events / max(total_events, 1),
            'learned_patterns': len(self.domain_patterns),
            'effective_patterns': len([p for p in self.domain_patterns.values() 
                                     if p.sample_count >= self.min_samples_for_pattern]),
            'top_patterns': [
                {
                    'pattern': p[0],
                    'success_rate': p[1].success_rate,
                    'sample_count': p[1].sample_count,
                    'confidence_boost': p[1].confidence_boost
                }
                for p in top_patterns[:5]
            ],
            'recent_activity': len(recent_events),
            'knowledge_base_size': sum(len(v) if isinstance(v, list) else 1 
                                     for v in self.knowledge_base.values())
        }
    
    def _initialize_industry_knowledge(self):
        """Initialize with spirits industry domain knowledge"""
        if not self.knowledge_base:
            self.knowledge_base = {
                'industry_keywords': [
                    'spirits', 'distillery', 'whiskey', 'bourbon', 'vodka', 'gin', 
                    'rum', 'tequila', 'wine', 'brewery', 'winery'
                ],
                'effective_search_terms': [
                    'official website', 'distillery', 'spirits', 'company'
                ],
                'domain_indicators': [
                    'distillery', 'spirits', 'wine', 'brewery'
                ],
                'false_positive_domains': [
                    'facebook', 'instagram', 'twitter', 'linkedin', 'wikipedia',
                    'yelp', 'tripadvisor', 'google', 'bing', 'yahoo', 'amazon',
                    'reddit', 'pinterest', 'youtube', 'tiktok', 'snapchat'
                ]
            }
            self._save_knowledge_base()
    
    def _update_knowledge_base(self, event: LearningEvent):
        """Update knowledge base with new learning"""
        
        # Add effective search terms from successful verifications
        if event.user_action == 'verified':
            # Extract potential search terms from features
            search_terms = event.features.get('search_terms_used', [])
            for term in search_terms:
                if term not in self.knowledge_base.get('effective_search_terms', []):
                    self.knowledge_base.setdefault('effective_search_terms', []).append(term)
        
        # Add false positive domains from rejections
        elif event.user_action == 'rejected':
            domain = event.domain
            if domain not in self.knowledge_base.get('false_positive_domains', []):
                self.knowledge_base.setdefault('false_positive_domains', []).append(domain)
        
        self._save_knowledge_base()
    
    def _add_discovered_pattern(self, pattern_type: str, pattern: str, event: LearningEvent):
        """Add a newly discovered pattern"""
        pattern_key = f"{pattern_type}:{pattern}"
        
        if pattern_key not in self.domain_patterns:
            self.domain_patterns[pattern_key] = DomainPattern(
                pattern=pattern,
                pattern_type=pattern_type,
                success_rate=1.0,  # Start with success since it was verified
                confidence_boost=0.1,  # Small initial boost
                sample_count=1,
                last_updated=datetime.now().isoformat()
            )
            
            logger.info(f"Discovered new pattern: {pattern_type}:{pattern}")
    
    def learn_from_selection(self, brand_name: str, selected_url: Optional[str], 
                           selected_rank: int, all_options: List[Dict], 
                           brand_context: Dict, user_feedback: str, 
                           rejection_reason: str = None):
        """
        Learn from user's website selection in multi-choice interface
        
        Args:
            brand_name: Brand being enriched
            selected_url: URL user selected (None if rejected all)
            selected_rank: Rank of selected option (1-3, 0 if rejected all)
            all_options: All options that were presented
            brand_context: Brand context information
            user_feedback: 'selected' or 'rejected_all'
            rejection_reason: Why user rejected all options
        """
        timestamp = datetime.now().isoformat()
        
        if user_feedback == 'selected' and selected_url:
            # User selected an option - learn from positive feedback
            selected_option = all_options[selected_rank - 1]
            
            # Create learning event for the selected option
            selected_event = LearningEvent(
                timestamp=timestamp,
                event_type='multi_choice_selection',
                brand_name=brand_name,
                domain=selected_option.get('domain', ''),
                confidence_predicted=selected_option.get('final_confidence', 0),
                user_action='selected',
                features=self._extract_features(brand_name, selected_url, brand_context),
                metadata={
                    'selection_rank': selected_rank,
                    'total_options': len(all_options),
                    'rejection_reason': None,
                    'all_options_summary': [
                        {
                            'rank': i + 1,
                            'domain': opt.get('domain', ''),
                            'confidence': opt.get('final_confidence', 0)
                        } for i, opt in enumerate(all_options)
                    ]
                }
            )
            
            self.learning_events.append(selected_event)
            
            # Create negative learning events for rejected options
            for i, option in enumerate(all_options):
                if i != (selected_rank - 1):  # Not the selected option
                    rejected_event = LearningEvent(
                        timestamp=timestamp,
                        event_type='multi_choice_rejection',
                        brand_name=brand_name,
                        domain=option.get('domain', ''),
                        confidence_predicted=option.get('final_confidence', 0),
                        user_action='not_selected',
                        features=self._extract_features(brand_name, option.get('url', ''), brand_context),
                        metadata={
                            'selected_rank': selected_rank,
                            'this_rank': i + 1,
                            'selected_domain': selected_option.get('domain', ''),
                            'total_options': len(all_options)
                        }
                    )
                    self.learning_events.append(rejected_event)
            
            # Update domain patterns based on selection
            self._update_patterns_from_selection(brand_name, selected_url, selected_rank, 
                                               all_options, brand_context)
            
            logger.info(f"📚 Learned from selection: {brand_name} -> {selected_option.get('domain', '')} "
                       f"(rank {selected_rank}/{len(all_options)})")
            
        elif user_feedback == 'rejected_all':
            # User rejected all options - learn what NOT to suggest
            for i, option in enumerate(all_options):
                rejected_event = LearningEvent(
                    timestamp=timestamp,
                    event_type='multi_choice_rejection_all',
                    brand_name=brand_name,
                    domain=option.get('domain', ''),
                    confidence_predicted=option.get('final_confidence', 0),
                    user_action='rejected_all',
                    features=self._extract_features(brand_name, option.get('url', ''), brand_context),
                    metadata={
                        'rejection_reason': rejection_reason,
                        'option_rank': i + 1,
                        'total_options': len(all_options)
                    }
                )
                self.learning_events.append(rejected_event)
            
            # Learn negative patterns from rejected options
            self._update_negative_patterns(brand_name, all_options, brand_context, rejection_reason)
            
            logger.info(f"📚 Learned from rejection: {brand_name} - rejected all {len(all_options)} options "
                       f"({rejection_reason})")
        
        # Save learning data
        self._save_learning_events()
        self._save_domain_patterns()
        self._save_knowledge_base()
        
        # Update knowledge base
        self._update_knowledge_base_from_selection(brand_name, selected_url, user_feedback, 
                                                 brand_context, rejection_reason)
    
    def _update_patterns_from_selection(self, brand_name: str, selected_url: str, 
                                      selected_rank: int, all_options: List[Dict], 
                                      brand_context: Dict):
        """Update domain patterns based on user selection"""
        selected_domain = None
        for opt in all_options:
            if opt.get('url') == selected_url:
                selected_domain = opt.get('domain', '')
                break
        
        if not selected_domain:
            return
        
        # Extract features that made this selection good
        features = self._extract_features(brand_name, selected_url, brand_context)
        
        # Boost patterns that match the selected option
        for feature_key, feature_value in features.items():
            if feature_value and isinstance(feature_value, (str, bool)):
                pattern_key = f"{feature_key}:{str(feature_value).lower()}"
                
                if pattern_key in self.domain_patterns:
                    pattern = self.domain_patterns[pattern_key]
                    pattern.sample_count += 1
                    # Boost confidence for good selections
                    if selected_rank == 1:  # First choice
                        pattern.confidence_boost = min(0.3, pattern.confidence_boost + 0.05)
                    elif selected_rank == 2:  # Second choice
                        pattern.confidence_boost = min(0.3, pattern.confidence_boost + 0.03)
                    else:  # Third choice
                        pattern.confidence_boost = min(0.3, pattern.confidence_boost + 0.01)
                    
                    pattern.last_updated = datetime.now().isoformat()
                else:
                    # Create new positive pattern
                    boost = 0.1 if selected_rank == 1 else 0.05
                    self.domain_patterns[pattern_key] = DomainPattern(
                        pattern=str(feature_value).lower(),
                        pattern_type=feature_key,
                        success_rate=1.0,
                        confidence_boost=boost,
                        sample_count=1,
                        last_updated=datetime.now().isoformat()
                    )
    
    def _update_negative_patterns(self, brand_name: str, rejected_options: List[Dict], 
                                brand_context: Dict, rejection_reason: str):
        """Learn negative patterns from rejected options"""
        for option in rejected_options:
            features = self._extract_features(brand_name, option.get('url', ''), brand_context)
            
            # Create negative patterns to avoid similar suggestions
            for feature_key, feature_value in features.items():
                if feature_value and isinstance(feature_value, (str, bool)):
                    pattern_key = f"negative_{feature_key}:{str(feature_value).lower()}"
                    
                    if pattern_key in self.domain_patterns:
                        pattern = self.domain_patterns[pattern_key]
                        pattern.sample_count += 1
                        # Reduce confidence for rejected patterns
                        pattern.confidence_boost = max(-0.2, pattern.confidence_boost - 0.02)
                    else:
                        # Create new negative pattern
                        self.domain_patterns[pattern_key] = DomainPattern(
                            pattern=str(feature_value).lower(),
                            pattern_type=f'negative_{feature_key}',
                            success_rate=0.0,
                            confidence_boost=-0.1,
                            sample_count=1,
                            last_updated=datetime.now().isoformat()
                        )
    
    def _extract_features(self, brand_name: str, url: str, brand_context: Dict) -> Dict[str, Any]:
        """Extract features for learning from brand and URL"""
        import re
        from urllib.parse import urlparse
        
        features = {}
        
        # URL parsing
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
        except:
            domain = url.lower()
            path = ''
        
        # Brand matching features
        brand_lower = brand_name.lower().replace(' ', '')
        brand_words = brand_name.lower().split()
        
        features['brand_in_domain'] = brand_lower in domain
        features['brand_words_in_domain'] = any(word in domain for word in brand_words if len(word) > 2)
        features['exact_brand_match'] = brand_lower == domain.replace('.com', '').replace('.net', '').replace('.org', '')
        
        # Industry context features
        industry_keywords = ['spirits', 'distillery', 'whiskey', 'bourbon', 'vodka', 'gin', 'rum', 'wine', 'brewery']
        features['has_industry_keyword'] = any(keyword in domain for keyword in industry_keywords)
        
        # Numeric patterns
        brand_numbers = re.findall(r'\d+', brand_name)
        domain_numbers = re.findall(r'\d+', domain)
        features['numeric_match'] = bool(brand_numbers and brand_numbers == domain_numbers)
        
        # Context features from brand_context
        if brand_context:
            features['product_types'] = brand_context.get('product_types', [])
            features['countries'] = brand_context.get('countries', [])
            features['sku_count'] = brand_context.get('sku_count', 0)
        
        # Domain quality features
        features['is_social_media'] = any(social in domain for social in ['facebook', 'instagram', 'twitter', 'linkedin'])
        features['is_marketplace'] = any(market in domain for market in ['amazon', 'ebay', 'walmart'])
        features['is_wiki'] = 'wikipedia' in domain
        features['tld'] = domain.split('.')[-1] if '.' in domain else 'unknown'
        
        return features

    def _update_knowledge_base_from_selection(self, brand_name: str, selected_url: Optional[str], 
                                            user_feedback: str, brand_context: Dict, 
                                            rejection_reason: str = None):
        """Update knowledge base with selection insights"""
        if 'multi_choice_learning' not in self.knowledge_base:
            self.knowledge_base['multi_choice_learning'] = {
                'total_selections': 0,
                'total_rejections': 0,
                'selection_rank_distribution': [0, 0, 0],  # Rank 1, 2, 3
                'common_rejection_reasons': {},
                'brand_patterns': {}
            }
        
        mc_learning = self.knowledge_base['multi_choice_learning']
        
        if user_feedback == 'selected':
            mc_learning['total_selections'] += 1
            # Find which rank was selected
            for i in range(3):
                if selected_url:  # Increment the rank that was selected
                    mc_learning['selection_rank_distribution'][0] += 1  # Simplified for now
                    break
        
        elif user_feedback == 'rejected_all':
            mc_learning['total_rejections'] += 1
            if rejection_reason:
                mc_learning['common_rejection_reasons'][rejection_reason] = \
                    mc_learning['common_rejection_reasons'].get(rejection_reason, 0) + 1
        
        # Track brand-specific patterns
        if brand_name not in mc_learning['brand_patterns']:
            mc_learning['brand_patterns'][brand_name] = {
                'selections': 0,
                'rejections': 0,
                'last_interaction': datetime.now().isoformat()
            }
        
        brand_pattern = mc_learning['brand_patterns'][brand_name]
        if user_feedback == 'selected':
            brand_pattern['selections'] += 1
        else:
            brand_pattern['rejections'] += 1
        brand_pattern['last_interaction'] = datetime.now().isoformat()
    
    # Data persistence methods
    def _load_learning_events(self) -> List[LearningEvent]:
        """Load learning events from file"""
        try:
            with open(self.events_file, 'r') as f:
                data = json.load(f)
                return [LearningEvent(**event) for event in data]
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error loading learning events: {e}")
            return []
    
    def _save_learning_events(self):
        """Save learning events to file"""
        try:
            with open(self.events_file, 'w') as f:
                json.dump([asdict(event) for event in self.learning_events], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving learning events: {e}")
    
    def _load_domain_patterns(self) -> Dict[str, DomainPattern]:
        """Load domain patterns from file"""
        try:
            with open(self.patterns_file, 'r') as f:
                data = json.load(f)
                return {k: DomainPattern(**v) for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading domain patterns: {e}")
            return {}
    
    def _save_domain_patterns(self):
        """Save domain patterns to file"""
        try:
            with open(self.patterns_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.domain_patterns.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving domain patterns: {e}")
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load knowledge base from file"""
        try:
            with open(self.knowledge_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            return {}
    
    def _save_knowledge_base(self):
        """Save knowledge base to file"""
        try:
            with open(self.knowledge_file, 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving knowledge base: {e}")
    
    # ===== NEW SEARCH STRATEGY LEARNING METHODS =====
    
    def record_search_strategy_success(self, brand_name: str, strategy_name: str, 
                                     search_query: str, brand_context: Dict, 
                                     results_quality: float, selected_domain: str):
        """Record successful search strategy for learning"""
        
        # Create learning event
        event = LearningEvent(
            timestamp=datetime.now().isoformat(),
            event_type='search_strategy',
            brand_name=brand_name,
            domain=selected_domain,
            confidence_predicted=results_quality,
            user_action='successful_search',
            features=self._extract_strategy_features(brand_name, brand_context),
            metadata={
                'strategy_name': strategy_name,
                'search_query': search_query,
                'results_quality': results_quality
            }
        )
        
        self.learning_events.append(event)
        self._save_learning_events()
        
        # Update strategy patterns
        self._update_strategy_patterns(brand_name, strategy_name, brand_context, results_quality)
        
        logger.info(f"📊 Recorded strategy success: {strategy_name} for {brand_name} (quality: {results_quality:.2f})")
    
    def _extract_strategy_features(self, brand_name: str, brand_context: Dict) -> Dict[str, Any]:
        """Extract features for strategy learning"""
        features = {}
        
        # Brand name characteristics
        features['starts_with_common_word'] = any(brand_name.lower().startswith(word) 
                                                for word in ['a ', 'the ', 'an ', 'and ', 'or '])
        features['has_numbers'] = bool(re.search(r'\d', brand_name))
        features['word_count'] = len(brand_name.split())
        features['brand_length'] = len(brand_name)
        
        # Context characteristics
        if brand_context:
            class_types = brand_context.get('class_types', [])
            countries = brand_context.get('countries', [])
            
            features['is_wine'] = any('wine' in ct.lower() for ct in class_types)
            features['is_spirits'] = any(term in ' '.join(class_types).lower() 
                                       for term in ['whiskey', 'bourbon', 'vodka', 'gin', 'rum', 'spirits'])
            features['is_beer'] = any(term in ' '.join(class_types).lower() 
                                    for term in ['beer', 'ale', 'malt', 'brewery'])
            features['has_location'] = len(countries) > 0
            features['is_us_brand'] = any('united states' in country.lower() for country in countries)
        
        return features
    
    def _update_strategy_patterns(self, brand_name: str, strategy_name: str, 
                                brand_context: Dict, results_quality: float):
        """Update search strategy patterns based on success"""
        
        features = self._extract_strategy_features(brand_name, brand_context)
        
        # Find or create strategy pattern
        strategy_key = self._get_strategy_key(strategy_name, features)
        
        if strategy_key not in self.strategy_patterns:
            self.strategy_patterns[strategy_key] = SearchStrategyPattern(
                strategy_name=strategy_name,
                brand_characteristics=features,
                success_rate=0.0,
                average_confidence=0.0,
                sample_count=0,
                examples=[],
                last_updated=datetime.now().isoformat()
            )
        
        pattern = self.strategy_patterns[strategy_key]
        
        # Update pattern statistics
        pattern.sample_count += 1
        pattern.success_rate = (pattern.success_rate * (pattern.sample_count - 1) + 1.0) / pattern.sample_count
        pattern.average_confidence = (pattern.average_confidence * (pattern.sample_count - 1) + results_quality) / pattern.sample_count
        pattern.last_updated = datetime.now().isoformat()
        
        # Add example (keep max 5)
        if brand_name not in pattern.examples:
            pattern.examples.append(brand_name)
            if len(pattern.examples) > 5:
                pattern.examples = pattern.examples[-5:]
        
        self._save_strategy_patterns()
    
    def _get_strategy_key(self, strategy_name: str, features: Dict[str, Any]) -> str:
        """Generate key for strategy pattern based on brand characteristics"""
        key_parts = [strategy_name]
        
        # Add relevant feature combinations
        if features.get('starts_with_common_word'):
            key_parts.append('common_word_start')
        if features.get('has_numbers'):
            key_parts.append('has_numbers')
        if features.get('is_wine'):
            key_parts.append('wine')
        elif features.get('is_spirits'):
            key_parts.append('spirits')
        elif features.get('is_beer'):
            key_parts.append('beer')
        
        return ':'.join(key_parts)
    
    def get_recommended_strategy(self, brand_name: str, brand_context: Dict) -> Optional[SearchStrategyPattern]:
        """Get recommended search strategy based on learned patterns"""
        
        features = self._extract_strategy_features(brand_name, brand_context)
        
        # Find matching strategy patterns
        matching_patterns = []
        for key, pattern in self.strategy_patterns.items():
            if pattern.sample_count >= 2:  # Minimum samples for recommendation
                # Check if brand characteristics match
                match_score = self._calculate_feature_match(features, pattern.brand_characteristics)
                if match_score > 0.5:  # 50% feature match threshold
                    matching_patterns.append((pattern, match_score))
        
        if matching_patterns:
            # Sort by success rate * confidence * match score
            matching_patterns.sort(key=lambda x: x[0].success_rate * x[0].average_confidence * x[1], reverse=True)
            best_pattern = matching_patterns[0][0]
            
            logger.info(f"🎯 Recommended strategy for {brand_name}: {best_pattern.strategy_name} "
                       f"(success: {best_pattern.success_rate:.1%}, confidence: {best_pattern.average_confidence:.2f})")
            
            return best_pattern
        
        # No learned patterns available
        return None

    def get_search_strategy_patterns(self) -> List[SearchStrategyPattern]:
        """Get all learned search strategy patterns"""
        return list(self.strategy_patterns.values())
    
    def _calculate_feature_match(self, features1: Dict, features2: Dict) -> float:
        """Calculate similarity between two feature sets"""
        common_keys = set(features1.keys()) & set(features2.keys())
        if not common_keys:
            return 0.0
        
        matches = sum(1 for key in common_keys if features1[key] == features2[key])
        return matches / len(common_keys)
    
    def _load_strategy_patterns(self) -> Dict[str, SearchStrategyPattern]:
        """Load search strategy patterns from file"""
        try:
            with open(self.strategy_patterns_file, 'r') as f:
                data = json.load(f)
                return {k: SearchStrategyPattern(**v) for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading strategy patterns: {e}")
            return {}
    
    def _load_relevance_patterns(self) -> Dict[str, RelevancePattern]:
        """Load relevance patterns from file"""
        try:
            with open(self.relevance_patterns_file, 'r') as f:
                data = json.load(f)
                return {k: RelevancePattern(**v) for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading relevance patterns: {e}")
            return {}
    
    def _save_relevance_patterns(self):
        """Save relevance patterns to file"""
        try:
            with open(self.relevance_patterns_file, 'w') as f:
                data = {k: asdict(v) for k, v in self.relevance_patterns.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving relevance patterns: {e}")
    
    def _save_strategy_patterns(self):
        """Save search strategy patterns to file"""
        try:
            with open(self.strategy_patterns_file, 'w') as f:
                json.dump({k: asdict(v) for k, v in self.strategy_patterns.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving strategy patterns: {e}")


def test_learning_system():
    """Test the agentic learning system"""
    print("🧠 Testing Agentic Learning System")
    print("=" * 50)
    
    # Initialize learning system
    learning = AgenticLearningSystem()
    
    # Simulate some user feedback
    test_cases = [
        {
            'brand_name': '1220 SPIRITS',
            'domain': '1220spirits.com',
            'predicted_confidence': 0.8,
            'user_action': 'verified',
            'features': {'brand_in_domain': True, 'industry_keyword': True}
        },
        {
            'brand_name': 'GREY GOOSE',
            'domain': 'greygoose.com',
            'predicted_confidence': 0.9,
            'user_action': 'verified',
            'features': {'brand_in_domain': True, 'exact_match': True}
        },
        {
            'brand_name': 'FAKE BRAND',
            'domain': 'facebook.com',
            'predicted_confidence': 0.7,
            'user_action': 'rejected',
            'features': {'social_media': True}
        }
    ]
    
    # Record feedback
    for case in test_cases:
        learning.record_user_feedback(**case)
    
    # Test enhanced confidence
    enhanced_conf = learning.get_enhanced_confidence(
        '1220 SPIRITS', '1220spirits.com', 0.8, 
        {'brand_in_domain': True, 'industry_keyword': True}
    )
    print(f"Enhanced confidence for 1220 SPIRITS: {enhanced_conf:.2f}")
    
    # Get learning insights
    insights = learning.get_learning_insights()
    print(f"\\nLearning Insights:")
    print(f"  Total events: {insights['total_learning_events']}")
    print(f"  Success rate: {insights['success_rate']:.2f}")
    print(f"  Learned patterns: {insights['learned_patterns']}")
    
    print("\\n✅ Learning system test complete!")


if __name__ == "__main__":
    test_learning_system()