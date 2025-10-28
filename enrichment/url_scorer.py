#!/usr/bin/env python3
"""
Enhanced URL Scoring System with Deep Snippet Analysis
Improves URL identification accuracy by analyzing descriptions more thoroughly
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EnhancedURLScorer:
    """
    Advanced URL scoring system that deeply analyzes snippets/descriptions
    to better identify official brand websites
    """
    
    def __init__(self):
        # Industry-specific terms with weights
        self.industry_terms = {
            # Primary alcohol production terms (highest weight)
            'distillery': 0.8,
            'brewery': 0.8,
            'winery': 0.8,
            'vineyard': 0.7,
            'cellar': 0.6,
            'distilling': 0.7,
            'brewing': 0.7,
            'winemaking': 0.7,
            
            # Product terms (high weight)
            'whiskey': 0.6,
            'whisky': 0.6,
            'bourbon': 0.6,
            'scotch': 0.6,
            'vodka': 0.6,
            'gin': 0.6,
            'rum': 0.6,
            'tequila': 0.6,
            'mezcal': 0.6,
            'brandy': 0.6,
            'cognac': 0.6,
            'wine': 0.5,
            'beer': 0.5,
            'spirits': 0.6,
            'liquor': 0.5,
            'liqueur': 0.5,
            
            # Production process terms (medium weight)
            'barrel': 0.4,
            'aged': 0.4,
            'craft': 0.4,
            'small batch': 0.5,
            'single malt': 0.5,
            'fermented': 0.4,
            'distilled': 0.5,
            'matured': 0.4,
            'cask': 0.4,
            'proof': 0.4,
            
            # Business terms (lower weight)
            'producer': 0.3,
            'manufacturer': 0.3,
            'maker': 0.3,
            'company': 0.2,
            'brand': 0.2
        }
        
        # Negative indicators (sites to avoid)
        self.negative_indicators = {
            # Social media (very negative)
            'facebook': -1.0,
            'instagram': -1.0,
            'twitter': -1.0,
            'linkedin': -1.0,
            'pinterest': -1.0,
            'tiktok': -1.0,
            'youtube': -1.0,
            'reddit': -1.0,
            
            # Forums and discussions (EXTREMELY negative)
            'forum': -1.0,
            'discussion': -1.0,
            'thread': -1.0,
            'comment': -1.0,
            'review': -0.8,
            'rating': -0.8,
            'board': -1.0,
            'community': -0.9,
            'talk': -0.9,
            'chat': -0.9,
            
            # Specific forum sites (block completely)
            'whiskybase': -1.0,
            'whiskyforum': -1.0,
            'connosr': -1.0,
            'straightbourbon': -1.0,
            'distillerytrail': -0.9,
            'cocktailtimes': -0.9,
            'spiritsreview': -0.9,
            
            # Aggregators and marketplaces (negative)
            'amazon': -1.0,
            'ebay': -1.0,
            'walmart': -1.0,
            'shop': -0.6,
            'store': -0.6,
            'buy': -0.6,
            'price': -0.7,
            'deal': -0.8,
            'discount': -0.8,
            'marketplace': -0.9,
            
            # Information sites (moderately negative)
            'wikipedia': -0.8,
            'wiki': -0.8,
            'encyclopedia': -0.8,
            'dictionary': -0.9,
            'definition': -0.8,
            
            # News and media (slightly negative)
            'news': -0.5,
            'article': -0.4,
            'blog': -0.6,
            'magazine': -0.4
        }
        
        # COMPLETE BLOCKLIST - these should never appear in results
        self.complete_blocklist = {
            # Social media
            'reddit.com', 'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'pinterest.com', 'tiktok.com', 'youtube.com', 
            # Alcohol forums and communities  
            'whiskybase.com', 'connosr.com', 'straightbourbon.com',
            'whiskyforum.com', 'bourbonforum.com', 'scotchwhisky.com',
            'cocktaildb.com', 'drinkspirit.com', 'spiritreview.com',
            'maltmadness.com', 'whiskycast.com', 'distillerytrail.com',
            # E-commerce/marketplace
            'amazon.com', 'ebay.com', 'walmart.com', 'target.com',
            'totalwine.com', 'wine.com', 'drizly.com', 'reservebar.com',
            # Information aggregators
            'wikipedia.org', 'wiki.com', 'fandom.com',
            'tripadvisor.com', 'yelp.com', 'foursquare.com',
            # News/blog aggregators (when they're not the official source)
            'buzzfeed.com', 'mashable.com', 'huffpost.com'
        }
        
        # Official website indicators
        self.official_indicators = {
            'official website': 1.0,
            'official site': 1.0,
            'homepage': 0.8,
            'welcome to': 0.7,
            'about us': 0.5,
            'our story': 0.6,
            'our distillery': 0.8,
            'our brewery': 0.8,
            'our winery': 0.8,
            'founded': 0.4,
            'established': 0.4,
            'since': 0.3,
            'family owned': 0.5,
            'award winning': 0.4,
            'premium': 0.3,
            'handcrafted': 0.4,
            'artisan': 0.4
        }
        
        # Geographic/location terms that suggest official presence
        self.location_indicators = {
            'visit us': 0.6,
            'location': 0.4,
            'tours': 0.5,
            'tasting room': 0.7,
            'visitor center': 0.6,
            'open hours': 0.5,
            'directions': 0.4
        }
    
    def is_blocked_domain(self, url: str, domain: str) -> bool:
        """Check if domain should be completely blocked"""
        domain_lower = domain.lower()
        
        # Check complete blocklist
        for blocked in self.complete_blocklist:
            if blocked in domain_lower:
                logger.info(f"🚫 Blocked domain detected: {domain} (matched: {blocked})")
                return True
        
        # Additional pattern-based blocking
        forum_patterns = ['forum', 'board', 'discussion', 'community', 'talk']
        for pattern in forum_patterns:
            if pattern in domain_lower:
                logger.info(f"🚫 Forum domain blocked: {domain}")
                return True
                
        return False
        
    def _get_learned_relevance_terms(self) -> Dict[str, List[str]]:
        """Get learned relevance terms from the learning system"""
        try:
            from .learning_system import AgenticLearningSystem
            learning_system = AgenticLearningSystem()
            return learning_system.get_learned_relevance_terms()
        except Exception as e:
            logger.error(f"Error getting learned relevance terms: {e}")
            return {'products': [], 'facilities': [], 'descriptors': [], 'negative_indicators': []}
    
    def _get_learned_negative_indicators(self) -> List[str]:
        """Get learned negative indicators from rejected URLs"""
        try:
            from .learning_system import AgenticLearningSystem
            learning_system = AgenticLearningSystem()
            learned_terms = learning_system.get_learned_relevance_terms()
            return learned_terms.get('negative_indicators', [])
        except Exception as e:
            logger.error(f"Error getting learned negative indicators: {e}")
            return []
    
    def _meets_strict_relevance_criteria(self, full_text: str, domain: str, brand_name: str) -> bool:
        """
        Strict filtering: URL must have either:
        1. Brand name + alcohol product type (whiskey, vodka, etc.)
        2. Facility type (distillery, winery, brewery) - brand can be in description
        3. Exact brand name match in domain or text
        """
        brand_lower = brand_name.lower()
        combined_text = f"{domain} {full_text}".lower()
        
        # Check for exact brand name match - but only if it has alcohol context
        if brand_lower in combined_text:
            # Base alcohol-related context terms
            alcohol_products = [
                'whiskey', 'whisky', 'bourbon', 'scotch', 'rye', 'tennessee whiskey',
                'irish whiskey', 'irish whisky', 'vodka', 'gin', 'rum', 'tequila', 
                'mezcal', 'brandy', 'cognac', 'wine', 'beer', 'ale', 'lager', 
                'stout', 'ipa', 'spirits', 'liquor', 'liqueur'
            ]
            
            alcohol_facilities = [
                'distillery', 'distilleries', 'distilling', 'distiller',
                'brewery', 'breweries', 'brewing', 'brewer', 'brewhouse',
                'winery', 'wineries', 'winemaker', 'vineyard', 'vintner'
            ]
            
            # ADAPTIVE LEARNING: Add learned terms from verified URLs
            learned_terms = self._get_learned_relevance_terms()
            if learned_terms:
                alcohol_products.extend(learned_terms['products'])
                alcohol_facilities.extend(learned_terms['facilities'])
                alcohol_products.extend(learned_terms['descriptors'])
                logger.info(f"🧠 Using {len(learned_terms['products']) + len(learned_terms['facilities']) + len(learned_terms['descriptors'])} learned relevance terms")
            
            alcohol_context = alcohol_products + alcohol_facilities
            
            has_alcohol_context = any(term in combined_text for term in alcohol_context)
            if has_alcohol_context:
                logger.info(f"✅ Relevance: Brand '{brand_name}' + alcohol context found")
                return True
            else:
                logger.info(f"❌ Brand '{brand_name}' found but no alcohol context")
        
        # Check for alcohol facility types (allow even without exact brand match)
        facility_types = [
            'distillery', 'distilleries', 'distilling', 'distiller',
            'brewery', 'breweries', 'brewing', 'brewer', 'brewhouse',
            'winery', 'wineries', 'winemaker', 'vineyard', 'vintner',
            'cellar', 'estate', 'château', 'chateau'
        ]
        
        for facility in facility_types:
            if facility in combined_text:
                logger.info(f"✅ Relevance: Alcohol facility '{facility}' found")
                return True
        
        # Check for brand name + alcohol product combinations
        alcohol_products = [
            'whiskey', 'whisky', 'bourbon', 'scotch', 'rye', 'tennessee',
            'vodka', 'gin', 'rum', 'tequila', 'mezcal', 'brandy', 'cognac',
            'wine', 'beer', 'ale', 'lager', 'stout', 'ipa', 'spirits',
            'liquor', 'liqueur'
        ]
        
        # Check if brand words appear near alcohol products
        brand_words = [word for word in brand_lower.split() if len(word) > 2]
        for brand_word in brand_words:
            if brand_word in combined_text:
                for product in alcohol_products:
                    if product in combined_text:
                        logger.info(f"✅ Relevance: Brand word '{brand_word}' + product '{product}' found")
                        return True
        
        # If none of the criteria are met, reject
        logger.info(f"❌ Irrelevant: No brand+product, facility, or exact match for '{brand_name}'")
        return False
    
    def score_url(self, result: Dict, brand_name: str, brand_context: Optional[Dict] = None) -> Tuple[float, Dict[str, float]]:
        """
        Score a URL based on comprehensive analysis of all available data
        
        Args:
            result: Search result containing url, title, snippet, domain
            brand_name: The brand being searched
            brand_context: Additional context (class_types, countries, etc.)
            
        Returns:
            Tuple of (final_score, score_components)
        """
        scores = {}
        
        # Extract data
        url = result.get('url', '').lower()
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        domain = result.get('domain', '').lower()
        
        # IMMEDIATE BLOCKING: Check if domain should be completely filtered out
        if self.is_blocked_domain(url, domain):
            return 0.0, {'blocked': 1.0}
        
        # Combine all text for analysis
        full_text = f"{title} {snippet}"
        
        # STRICT RELEVANCE: Must meet alcohol industry relevance criteria
        if not self._meets_strict_relevance_criteria(full_text, domain, brand_name):
            return 0.0, {'irrelevant': 1.0}
        
        # 1. Domain Analysis (30% weight)
        scores['domain'] = self._score_domain(domain, brand_name)
        
        # 2. Brand Name Matching (25% weight)
        scores['brand_match'] = self._score_brand_match(full_text, domain, brand_name)
        
        # 3. Industry Relevance from Snippet (20% weight)
        scores['industry'] = self._score_industry_relevance(full_text, brand_context)
        
        # 4. Official Indicators (15% weight)
        scores['official'] = self._score_official_indicators(full_text)
        
        # 5. Negative Indicators (10% weight penalty)
        scores['negative'] = self._score_negative_indicators(full_text, domain)
        
        # 6. Context Matching (bonus up to 10%)
        if brand_context:
            scores['context'] = self._score_context_match(full_text, brand_context)
        else:
            scores['context'] = 0.0
        
        # Calculate weighted final score
        weights = {
            'domain': 0.30,
            'brand_match': 0.25,
            'industry': 0.20,
            'official': 0.15,
            'negative': 0.10,  # This will be subtracted
            'context': 0.10   # Bonus
        }
        
        final_score = 0.0
        for component, weight in weights.items():
            if component == 'negative':
                # Negative score reduces overall score
                final_score -= abs(scores[component]) * weight
            else:
                final_score += scores[component] * weight
        
        # Ensure score is between 0 and 1
        final_score = max(0.0, min(1.0, final_score))
        
        return final_score, scores
    
    def _score_domain(self, domain: str, brand_name: str) -> float:
        """Score domain quality and brand matching"""
        score = 0.0
        
        # Clean domain
        domain_clean = domain.replace('www.', '').lower()
        brand_clean = brand_name.lower().replace(' ', '')
        brand_words = [w.lower() for w in brand_name.split() if len(w) > 2]
        
        # Exact brand match in domain (highest score)
        if brand_clean in domain_clean.replace('.', ''):
            score = 0.9
        # All significant brand words in domain
        elif all(word in domain_clean for word in brand_words):
            score = 0.7
        # Some brand words in domain
        elif any(word in domain_clean for word in brand_words):
            score = 0.5
        
        # Numeric brand matching (e.g., "1220" in "1220spirits.com")
        brand_numbers = re.findall(r'\d+', brand_name)
        domain_numbers = re.findall(r'\d+', domain_clean)
        if brand_numbers and brand_numbers == domain_numbers:
            score = max(score, 0.8)
        
        # Boost for .com domains
        if domain_clean.endswith('.com'):
            score += 0.1
        
        # Penalty for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf']
        if any(domain_clean.endswith(tld) for tld in suspicious_tlds):
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def _score_brand_match(self, text: str, domain: str, brand_name: str) -> float:
        """Enhanced brand matching including distillery-brand relationships"""
        score = 0.0
        brand_lower = brand_name.lower()
        brand_words = brand_lower.split()
        
        # Direct brand mentions (highest priority)
        brand_count = text.count(brand_lower)
        if brand_count >= 3:
            score = 0.9
        elif brand_count == 2:
            score = 0.7
        elif brand_count == 1:
            score = 0.5
        
        # Check for brand in key positions
        if text.startswith(brand_lower):
            score += 0.1
        if f"welcome to {brand_lower}" in text:
            score = 1.0
        if f"{brand_lower} distillery" in text or f"{brand_lower} brewery" in text or f"{brand_lower} winery" in text:
            score = max(score, 0.9)
        
        # ENHANCED: Distillery-Brand relationship detection
        # Look for patterns like "XYZ Distillery produces ABC Brand" or "ABC is made by XYZ"
        distillery_brand_patterns = [
            rf"(\w+(?:\s+\w+)*)\s+(?:distillery|brewery|winery)\s+(?:produces?|makes?|crafts?)\s+(?:the\s+)?{re.escape(brand_lower)}",
            rf"{re.escape(brand_lower)}\s+(?:is\s+)?(?:made|produced|crafted|distilled|brewed)\s+(?:by|at)\s+(\w+(?:\s+\w+)*)\s+(?:distillery|brewery|winery)",
            rf"(?:from|by)\s+(\w+(?:\s+\w+)*)\s+(?:distillery|brewery|winery).*{re.escape(brand_lower)}",
            rf"{re.escape(brand_lower)}.*(?:from|by)\s+(\w+(?:\s+\w+)*)\s+(?:distillery|brewery|winery)",
            rf"(\w+(?:\s+\w+)*)\s+(?:distillery|brewery|winery).*(?:flagship|premium|signature)\s+(?:brand\s+)?{re.escape(brand_lower)}"
        ]
        
        for pattern in distillery_brand_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                logger.info(f"🔍 Found distillery-brand relationship: {match.group(0)}")
                score = max(score, 0.85)  # High score for detected relationships
        
        # ENHANCED: Product portfolio detection
        # Look for "our brands include", "portfolio includes", etc.
        portfolio_patterns = [
            rf"(?:our\s+)?(?:brands?|portfolio|products?)\s+(?:include|feature)s?\s+.*{re.escape(brand_lower)}",
            rf"{re.escape(brand_lower)}\s+(?:is\s+)?(?:one\s+of\s+)?(?:our|their)\s+(?:flagship|premium|signature|main)\s+(?:brands?|products?)",
            rf"(?:featuring|including|offering)\s+.*{re.escape(brand_lower)}.*(?:vodka|whiskey|whisky|gin|rum|bourbon|spirits?)",
            rf"(?:makers?\s+of|producers?\s+of|creators?\s+of)\s+.*{re.escape(brand_lower)}"
        ]
        
        for pattern in portfolio_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"🎯 Found brand portfolio mention: {brand_name}")
                score = max(score, 0.8)
        
        # ENHANCED: Partial word matching for compound brand names
        # If brand has multiple words, check if key words appear in context
        if len(brand_words) > 1:
            key_words_found = 0
            for word in brand_words:
                if len(word) > 2:  # Skip short words like "A", "TO", "THE"
                    if word in text:
                        key_words_found += 1
            
            if key_words_found >= len([w for w in brand_words if len(w) > 2]) * 0.7:  # 70% of key words
                logger.info(f"🔤 Found {key_words_found} key words from brand: {brand_name}")
                score = max(score, 0.6)
        
        # ENHANCED: Domain-text relationship bonus
        # If domain contains part of brand name and text mentions the brand
        domain_words = re.findall(r'\w+', domain)
        brand_in_domain = any(word in ''.join(domain_words) for word in brand_words if len(word) > 2)
        if brand_in_domain and score > 0:
            score += 0.2  # Bonus for domain-text alignment
            logger.info(f"🌐 Domain-text alignment bonus for: {brand_name}")
        
        return min(1.0, score)
    
    def _score_industry_relevance(self, text: str, brand_context: Optional[Dict]) -> float:
        """Enhanced industry relevance scoring with context awareness"""
        score = 0.0
        term_count = 0
        
        # Check for industry terms
        for term, weight in self.industry_terms.items():
            if term in text:
                score += weight
                term_count += 1
        
        # Normalize by number of terms found (diminishing returns)
        if term_count > 0:
            score = score / (1 + term_count * 0.3)  # Diminishing returns factor
        
        # ENHANCED: Context-aware scoring with detailed product matching
        if brand_context and brand_context.get('class_types'):
            class_types = ' '.join(brand_context['class_types']).lower()
            
            # Specific product type matching with higher precision
            whiskey_terms = ['whiskey', 'whisky', 'bourbon', 'scotch', 'rye', 'tennessee', 'irish']
            wine_terms = ['wine', 'winery', 'vineyard', 'vintner', 'cellar', 'estate', 'château']
            beer_terms = ['beer', 'brewery', 'brewing', 'ale', 'lager', 'stout', 'ipa', 'pilsner']
            vodka_terms = ['vodka', 'premium vodka', 'craft vodka', 'potato vodka', 'wheat vodka']
            gin_terms = ['gin', 'dry gin', 'london gin', 'craft gin', 'botanical']
            
            if any(w in class_types for w in ['whiskey', 'whisky', 'bourbon', 'rye', 'scotch']):
                matches = sum(1 for term in whiskey_terms if term in text)
                score += min(0.4, matches * 0.15)  # Up to 0.4 bonus
                if matches > 0:
                    logger.info(f"🥃 Whiskey context match: {matches} terms found")
                    
            elif 'wine' in class_types:
                matches = sum(1 for term in wine_terms if term in text)
                score += min(0.4, matches * 0.15)
                if matches > 0:
                    logger.info(f"🍷 Wine context match: {matches} terms found")
                    
            elif any(w in class_types for w in ['beer', 'ale', 'lager', 'stout']):
                matches = sum(1 for term in beer_terms if term in text)
                score += min(0.4, matches * 0.15)
                if matches > 0:
                    logger.info(f"🍺 Beer context match: {matches} terms found")
                    
            elif 'vodka' in class_types:
                matches = sum(1 for term in vodka_terms if term in text)
                score += min(0.4, matches * 0.15)
                if matches > 0:
                    logger.info(f"🍸 Vodka context match: {matches} terms found")
                    
            elif 'gin' in class_types:
                matches = sum(1 for term in gin_terms if term in text)
                score += min(0.4, matches * 0.15)
                if matches > 0:
                    logger.info(f"🍶 Gin context match: {matches} terms found")
        
        # ENHANCED: Geographic context matching
        if brand_context and brand_context.get('countries'):
            for country in brand_context['countries']:
                country_lower = country.lower()
                if country_lower in text:
                    score += 0.2
                    logger.info(f"🌍 Geographic context match: {country}")
                    break
                    
                # Check for region-specific terms
                if country_lower in ['scotland', 'united kingdom']:
                    if any(term in text for term in ['scottish', 'highland', 'lowland', 'speyside', 'islay']):
                        score += 0.25
                        logger.info(f"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scottish regional context found")
                        
                elif country_lower == 'ireland':
                    if any(term in text for term in ['irish', 'dublin', 'cork', 'jameson']):
                        score += 0.25
                        logger.info(f"🇮🇪 Irish regional context found")
                        
                elif country_lower in ['united states', 'usa']:
                    if any(term in text for term in ['kentucky', 'tennessee', 'bourbon trail', 'american']):
                        score += 0.2
                        logger.info(f"🇺🇸 American regional context found")
        
        return min(1.0, score)
    
    def _score_official_indicators(self, text: str) -> float:
        """Score based on indicators of an official website"""
        score = 0.0
        
        for indicator, weight in self.official_indicators.items():
            if indicator in text:
                score = max(score, weight)  # Take highest indicator
        
        # Additional checks for location/visit information
        for indicator, weight in self.location_indicators.items():
            if indicator in text:
                score = max(score, score + weight * 0.5)  # Add half weight as bonus
        
        return min(1.0, score)
    
    def _score_negative_indicators(self, text: str, domain: str) -> float:
        """Calculate negative score based on unwanted indicators including learned patterns"""
        negative_score = 0.0
        
        # Check built-in negative indicators
        for indicator, weight in self.negative_indicators.items():
            if indicator in domain:
                negative_score = min(negative_score, weight * 1.5)  # Domain presence is worse
            elif indicator in text:
                negative_score = min(negative_score, weight)
        
        # REJECTION LEARNING: Check learned negative indicators from rejected URLs
        learned_negative = self._get_learned_negative_indicators()
        for negative_term in learned_negative:
            if negative_term.lower() in text.lower() or negative_term.lower() in domain.lower():
                # Apply strong negative weight to learned patterns
                penalty = -0.8 if negative_term.lower() in domain.lower() else -0.6
                negative_score = min(negative_score, penalty)
                logger.info(f"🚫 Learned negative pattern detected: '{negative_term}' in {'domain' if negative_term.lower() in domain.lower() else 'text'}")
        
        return abs(negative_score)  # Return positive value for subtraction
    
    def _score_context_match(self, text: str, brand_context: Dict) -> float:
        """Score based on matching brand context"""
        score = 0.0
        
        # Country matching
        if brand_context.get('countries'):
            for country in brand_context['countries']:
                if country.lower() in text:
                    score += 0.3
                    break
        
        # Producer matching
        if brand_context.get('producers'):
            for producer in brand_context['producers']:
                if producer.lower() in text:
                    score += 0.4
                    break
        
        # SKU count indicator (established brands)
        if brand_context.get('sku_count', 0) > 10:
            if any(term in text for term in ['established', 'since', 'founded', 'heritage']):
                score += 0.2
        
        return min(1.0, score)
    
    def rank_urls(self, results: List[Dict], brand_name: str, brand_context: Optional[Dict] = None) -> List[Dict]:
        """
        Rank a list of URLs by their scores
        
        Args:
            results: List of search results
            brand_name: The brand being searched
            brand_context: Additional context
            
        Returns:
            List of results sorted by score with added scoring information
        """
        scored_results = []
        blocked_count = 0
        
        for result in results:
            score, components = self.score_url(result, brand_name, brand_context)
            
            # Skip blocked domains (score = 0.0 with 'blocked' component)
            if score == 0.0 and components.get('blocked'):
                blocked_count += 1
                continue
            
            # Add scoring information to result
            result_with_score = result.copy()
            result_with_score['enhanced_score'] = score
            result_with_score['score_components'] = components
            result_with_score['score_explanation'] = self._generate_explanation(components)
            
            scored_results.append(result_with_score)
        
        if blocked_count > 0:
            logger.info(f"🚫 Filtered out {blocked_count} blocked/forum domains")
        
        # Sort by enhanced score (highest first)
        scored_results.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        return scored_results
    
    def _generate_explanation(self, components: Dict[str, float]) -> str:
        """Generate human-readable explanation of scoring"""
        explanations = []
        
        if components.get('domain', 0) > 0.7:
            explanations.append("Strong domain match")
        elif components.get('domain', 0) > 0.4:
            explanations.append("Partial domain match")
        
        if components.get('brand_match', 0) > 0.7:
            explanations.append("Multiple brand mentions")
        
        if components.get('industry', 0) > 0.6:
            explanations.append("High industry relevance")
        elif components.get('industry', 0) > 0.3:
            explanations.append("Industry-related content")
        
        if components.get('official', 0) > 0.7:
            explanations.append("Official website indicators")
        
        if components.get('negative', 0) > 0.5:
            explanations.append("⚠️ Contains negative indicators")
        
        if components.get('context', 0) > 0.3:
            explanations.append("Matches brand context")
        
        return " • ".join(explanations) if explanations else "General result"