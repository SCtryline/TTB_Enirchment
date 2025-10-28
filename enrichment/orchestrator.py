#!/usr/bin/env python3
"""
Integrated Brand Enrichment System
Combines safe search with founder discovery and Apollo.io integration
"""

import os
import json
import re
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from .safe_search import SafeSearchSystem
from .search_engine import ProductionSearchWrapper
from .learning_system import AgenticLearningSystem
from .url_scorer import EnhancedURLScorer
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedEnrichmentSystem:
    """
    Complete enrichment pipeline: Safe Search → Founder Discovery → Apollo.io
    """
    
    def __init__(self, apollo_api_key: Optional[str] = None, environment: str = None):
        # Get Apollo API key from environment or parameter
        self.apollo_api_key = apollo_api_key or os.getenv('APOLLO_API_KEY')
        
        # FORCE PRODUCTION MODE for high-quality results
        self.environment = 'production'  # Override to always use production search
        
        # Initialize production search system for high-quality results
        self.fast_searcher = None
        self.use_fast_mode = False
        logger.info("🔒 Using PRODUCTION search mode for high-quality results (30-60s per search)")
        
        # Initialize search systems (HTTP-based and Production Browser-based)
        self.searcher = SafeSearchSystem(use_proxies=False, use_tor=False)
        
        # Only initialize browser searcher if not in fast mode
        if not self.use_fast_mode:
            self.browser_searcher = ProductionSearchWrapper(
                use_proxies=False,     # Set to True to enable IP rotation
                paid_proxies=False     # Set to True for production proxy services
            )
        else:
            self.browser_searcher = None
        
        # Initialize agentic learning system
        self.learning_agent = AgenticLearningSystem()
        
        # Initialize Enhanced URL Scorer for better snippet analysis
        self.url_scorer = EnhancedURLScorer()
        
        # Enrichment results storage
        self.results_file = 'data/enrichment_results.json'
        self.load_results()
        
        # Founder name patterns
        self.founder_patterns = [
            # Direct patterns
            r'(?:founder|ceo|owner|president|proprietor)(?:\s+and\s+\w+)?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})[\s,]+(?:founder|ceo|owner|president)',
            r'(?:founded\s+by|established\s+by|created\s+by|started\s+by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            
            # Industry-specific
            r'(?:master\s+)?(?:distiller|winemaker|brewmaster|vintner)[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}),?\s+(?:master\s+)?(?:distiller|winemaker|brewmaster)',
            
            # Company formation patterns
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:founded|established|started|launched)\s+(?:the\s+)?(?:company|distillery|winery|brewery)',
        ]
        
        # Title keywords for validation
        self.executive_titles = [
            'founder', 'co-founder', 'owner', 'co-owner', 'ceo', 'president',
            'chief executive', 'managing director', 'proprietor',
            'distiller', 'master distiller', 'head distiller',
            'winemaker', 'head winemaker', 'vintner',
            'brewmaster', 'head brewer', 'brewing director'
        ]

    def _record_strategy_success(self, strategy_name: str, brand_name: str, brand_context: Optional[Dict], results: List[Dict]):
        """Record successful search strategy for learning"""
        try:
            # Extract brand characteristics for pattern learning
            brand_characteristics = self._extract_brand_characteristics(brand_name, brand_context)
            
            # Calculate success metrics
            high_conf_results = [r for r in results if r.get('confidence', 0) >= 0.6]
            average_confidence = sum(r.get('confidence', 0) for r in results) / len(results) if results else 0
            
            # Record the successful strategy
            top_result = results[0] if results else {}
            selected_domain = top_result.get('domain', top_result.get('url', 'unknown'))
            
            self.learning_agent.record_search_strategy_success(
                brand_name=brand_name,
                strategy_name=strategy_name,
                search_query=f"Search for {brand_name}",
                brand_context=brand_context or {},
                results_quality=average_confidence,
                selected_domain=selected_domain
            )
            
            logger.info(f"📚 Recorded successful strategy '{strategy_name}' for '{brand_name}' (avg conf: {average_confidence:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to record strategy success: {e}")
            
    def _extract_brand_characteristics(self, brand_name: str, brand_context: Optional[Dict]) -> Dict[str, Any]:
        """Extract characteristics for pattern learning"""
        characteristics = {
            'brand_length': len(brand_name),
            'has_numbers': any(c.isdigit() for c in brand_name),
            'has_spaces': ' ' in brand_name,
            'word_count': len(brand_name.split()),
            'starts_with_common': any(brand_name.lower().startswith(word) for word in ['a ', 'the ', 'an ', 'and ', 'or ']),
            'is_numerical': any(c.isdigit() for c in brand_name) and len(brand_name) <= 6,
            'has_special_chars': any(c in brand_name for c in ['.', '&', '-', "'"])
        }
        
        if brand_context:
            characteristics.update({
                'has_class_types': bool(brand_context.get('class_types')),
                'primary_class_type': brand_context.get('class_types', [None])[0],
                'has_countries': bool(brand_context.get('countries')),
                'primary_country': brand_context.get('countries', [None])[0],
                'sku_count': len(brand_context.get('skus', [])) if brand_context.get('skus') else 0
            })
            
        return characteristics
    
    def _is_alcohol_related(self, result: Dict, brand_name: str) -> bool:
        """Check if a search result is alcohol/beverage related - LESS STRICT for better results"""
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        url = result.get('url', '').lower()
        domain = result.get('domain', '').lower()
        
        # Expanded alcohol-related terms (more inclusive)
        alcohol_terms = [
            'whiskey', 'whisky', 'bourbon', 'distillery', 'spirits', 
            'brewery', 'brewing', 'brewer', 'wine', 'winery', 'vineyard',
            'vodka', 'rum', 'gin', 'tequila', 'mezcal',
            'liqueur', 'liquor', 'alcohol', 'alcoholic', 'beverage', 'drinks', 
            'scotch', 'rye', 'brandy', 'cognac', 'proof',
            # More inclusive terms
            'beer', 'ale', 'lager', 'stout', 'ipa', 'craft', 'tap', 'taproom',
            'bar', 'pub', 'cocktail', 'bottle', 'barrel', 'cask', 'aged',
            'fermented', 'distilled', 'premium', 'reserve', 'vintage'
        ]
        
        # Strong indicators in domain (if brand is in domain + alcohol term, very likely correct)
        domain_alcohol_terms = [
            'distillery', 'brewery', 'winery', 'spirits', 'wine', 'whiskey',
            'vodka', 'gin', 'rum', 'beer', 'brewing'
        ]
        
        # Historical/non-alcohol terms to avoid (but be less strict)
        avoid_terms = [
            'wikipedia', 'history museum', 'historical society', 'archive.org',
            'biography.com', 'encyclopedia', 'timeline of', 'born in', 'died in',
            'medieval', 'ancient', '15th century', '16th century', 'civil war'
        ]
        
        content = f"{title} {snippet} {url}"
        brand_lower = brand_name.lower()
        
        # Check for strong domain indicators (domain + alcohol term = very likely correct)
        has_domain_alcohol = any(term in domain for term in domain_alcohol_terms)
        
        # Check for brand name presence
        has_brand = brand_lower in content or any(word in content for word in brand_lower.split() if len(word) > 3)
        
        # Check for alcohol terms
        has_alcohol = any(term in content for term in alcohol_terms)
        
        # Check for historical content (be more specific)
        is_historical = any(term in content for term in avoid_terms)
        
        # LESS STRICT LOGIC: Multiple ways to pass
        if is_historical:
            return False  # Definitely reject historical content
        
        # Pass if: (Brand in domain + alcohol term) OR (has alcohol terms + brand present) OR (strong alcohol indicators)
        if has_domain_alcohol and has_brand:
            return True  # Strong signal: brand domain with alcohol terms
        
        if has_alcohol and has_brand:
            return True  # Standard case: alcohol content mentioning brand
        
        if has_alcohol and any(strong_term in content for strong_term in ['official', 'distillery', 'brewery', 'winery']):
            return True  # Strong alcohol business indicators
        
        # Even if no explicit brand mention, allow strong alcohol businesses
        if any(strong_term in title for strong_term in ['distillery', 'brewery', 'winery', 'spirits']):
            return True
        
        return False
    
    def intelligent_brand_search(self, brand_name: str, brand_context: Optional[Dict] = None) -> List[Dict]:
        """
        Intelligent brand search with fallback strategies using brand context
        Enhanced with agentic learning to optimize search strategy order
        """
        import time
        start_time = time.time()
        timeout_seconds = 45  # 45 second timeout for better UI responsiveness
        
        results = []
        
        # Get recommended strategy based on learning patterns
        brand_characteristics = self._extract_brand_characteristics(brand_name, brand_context)
        recommended_strategy = self.learning_agent.get_recommended_strategy(brand_name, brand_characteristics)
        
        if recommended_strategy:
            logger.info(f"🧠 AI recommends '{recommended_strategy.strategy_name}' strategy (success rate: {recommended_strategy.success_rate:.2%})")
            
            # Try recommended strategy first if it's different from default
            if recommended_strategy.strategy_name == "strategy_simple_unquoted" and not any(brand_name.lower().startswith(word) for word in ['a ', 'the ', 'an ', 'and ', 'or ']):
                logger.info(f"🎯 Trying AI-recommended simple unquoted search first")
                simple_results = self.hybrid_search(brand_name)
                if simple_results:
                    good_results = [r for r in simple_results if self._is_alcohol_related(r, brand_name)]
                    if good_results and any(r.get('confidence', 0) >= 0.6 for r in good_results):
                        logger.info(f"✅ AI-recommended strategy succeeded immediately!")
                        self._record_strategy_success("strategy_simple_unquoted", brand_name, brand_context, good_results)
                        return good_results
            
            elif recommended_strategy.strategy_name == "strategy_quoted_industry":
                logger.info(f"🎯 Trying AI-recommended quoted + industry search first")
                for industry_term in ['distillery', 'spirits', 'winery', 'brewery']:
                    quoted_results = self.hybrid_search(f'"{brand_name}" {industry_term}')
                    if quoted_results:
                        good_results = [r for r in quoted_results if self._is_alcohol_related(r, brand_name)]
                        if good_results and any(r.get('confidence', 0) >= 0.6 for r in good_results):
                            logger.info(f"✅ AI-recommended quoted + industry strategy succeeded!")
                            self._record_strategy_success("strategy_quoted_industry", brand_name, brand_context, good_results)
                            return good_results
        
        # For numerical brands like "1835", prioritize alcohol-specific searches first
        is_numerical_brand = any(char.isdigit() for char in brand_name) and len(brand_name) <= 6
        
        if is_numerical_brand:
            # Strategy 1 for numerical brands: Brand + alcohol terms first (UNQUOTED for better results)
            logger.info(f"🎯 Strategy 1 (Numerical): Brand + alcohol terms for '{brand_name}'")
            
            # Try different alcohol contexts - UNQUOTED for better ranking
            alcohol_searches = [
                f'{brand_name} bourbon whiskey',
                f'{brand_name} distillery',  
                f'{brand_name} spirits',
                f'{brand_name} Texas bourbon' if brand_context and 'TEXAS' in str(brand_context.get('countries', [])) else None
            ]
            
            for search_term in alcohol_searches:
                if not search_term:
                    continue
                if time.time() - start_time > timeout_seconds:
                    break
                    
                alcohol_results = self.hybrid_search(search_term)
                if alcohol_results:
                    # Filter for alcohol-related results
                    filtered_results = [r for r in alcohol_results if self._is_alcohol_related(r, brand_name)]
                    if filtered_results:
                        logger.info(f"✅ Found {len(filtered_results)} alcohol-related results")
                        # Record successful numerical brand strategy
                        self._record_strategy_success("strategy_numerical_alcohol", brand_name, brand_context, filtered_results)
                        results.extend(filtered_results)
                        break
        
        # Strategy 1 (Original): Direct brand name search - but only if not numerical or no alcohol results found
        if not results and not is_numerical_brand:
            if time.time() - start_time > timeout_seconds:
                logger.warning("Timeout reached, stopping search")
                return results
                
            logger.info(f"🎯 Strategy 1: Direct brand search for '{brand_name}' (UNQUOTED PRIMARY)")
            
            # NEW APPROACH: Unquoted searches first since they rank brands higher at top of results
            logger.info(f"🔍 Trying unquoted search first (brands appear higher in results)")
            results = self.hybrid_search(brand_name)
            
            if results:
                # Filter for alcohol-related results
                good_results = [r for r in results if self._is_alcohol_related(r, brand_name)]
                if good_results and any(r.get('confidence', 0) >= 0.5 for r in good_results):
                    logger.info(f"✅ Unquoted search succeeded with {len(good_results)} relevant results")
                    self._record_strategy_success("strategy_unquoted_primary", brand_name, brand_context, good_results)
                    results = good_results
                else:
                    logger.info(f"🔄 Unquoted found {len(results)} results but need better alcohol relevance")
            
            # If unquoted didn't work well, try with industry terms (still unquoted for better ranking)
            if not results or len([r for r in results if self._is_alcohol_related(r, brand_name)]) < 2:
                logger.info(f"🎯 Trying unquoted + industry terms")
                industry_searches = [
                    f'{brand_name} distillery',
                    f'{brand_name} winery', 
                    f'{brand_name} brewery',
                    f'{brand_name} spirits'
                ]
                
                for search_term in industry_searches:
                    attempt_results = self.hybrid_search(search_term)
                    if attempt_results:
                        good_results = [r for r in attempt_results if self._is_alcohol_related(r, brand_name)]
                        if good_results:
                            logger.info(f"✅ Found relevant results with unquoted + industry: {search_term}")
                            self._record_strategy_success("strategy_unquoted_industry", brand_name, brand_context, good_results)
                            results.extend(good_results)
                            break
            
            # Only use quoted search as final fallback if unquoted completely fails
            if not results:
                logger.info(f"🔄 Final fallback: quoted search")
                results = self.hybrid_search(f'"{brand_name}"')
            
            if results and any(r.get('confidence', 0) >= 0.6 for r in results):
                logger.info(f"✅ Strategy 1 succeeded with high-confidence results")
                # Record successful strategy for learning
                self._record_strategy_success("strategy_1_direct", brand_name, brand_context, results)
                return results
        
        # Strategy 2: Brand name + product type
        if time.time() - start_time > timeout_seconds:
            logger.warning("Timeout reached, stopping at Strategy 2")
            return results
            
        if brand_context and brand_context.get('class_types'):
            class_type = brand_context['class_types'][0] if brand_context['class_types'] else ''
            if class_type:
                # Clean up class type for search - UNQUOTED for better ranking
                clean_type = class_type.replace('STRAIGHT ', '').replace(' WHISKY', ' WHISKEY')
                search_query = f'{brand_name} {clean_type.lower()}'
                logger.info(f"🎯 Strategy 2: Brand + product type: '{search_query}' (UNQUOTED)")
                
                fallback_results = self.hybrid_search(search_query)
                if fallback_results and any(r.get('confidence', 0) >= 0.6 for r in fallback_results):
                    logger.info(f"✅ Strategy 2 succeeded with product type context")
                    # Record successful strategy for learning
                    self._record_strategy_success("strategy_2_product_type", brand_name, brand_context, fallback_results)
                    return fallback_results
                
                # Merge results if we found something
                if fallback_results:
                    results.extend(fallback_results)
        
        # Strategy 3: Brand name + origin/location
        if time.time() - start_time > timeout_seconds:
            logger.warning("Timeout reached, stopping at Strategy 3")
            return results
            
        if brand_context and brand_context.get('countries'):
            origin = brand_context['countries'][0] if brand_context['countries'] else ''
            if origin and origin.upper() not in ['UNITED STATES', 'USA']:  # More specific than USA
                search_query = f'{brand_name} {origin.lower()}'
                logger.info(f"🎯 Strategy 3: Brand + origin: '{search_query}' (UNQUOTED)")
                
                fallback_results = self.hybrid_search(search_query)
                if fallback_results and any(r.get('confidence', 0) >= 0.6 for r in fallback_results):
                    logger.info(f"✅ Strategy 3 succeeded with origin context")
                    # Record successful strategy for learning
                    self._record_strategy_success("strategy_3_origin", brand_name, brand_context, fallback_results)
                    return fallback_results
                
                if fallback_results:
                    results.extend(fallback_results)
        
        # Strategy 4: Combined context search (skip if we already have good results)
        if time.time() - start_time > timeout_seconds or len(results) >= 10:
            logger.info("Stopping search - timeout or sufficient results")
            return results[:10]
            
        if brand_context and brand_context.get('class_types') and brand_context.get('countries'):
            class_type = brand_context['class_types'][0] if brand_context['class_types'] else ''
            origin = brand_context['countries'][0] if brand_context['countries'] else ''
            
            if class_type and origin:
                clean_type = class_type.replace('STRAIGHT ', '').replace(' WHISKY', ' WHISKEY')
                search_query = f'{brand_name} {clean_type.lower()} {origin.lower()}'
                logger.info(f"🎯 Strategy 4: Brand + type + origin: '{search_query}' (UNQUOTED)")
                
                fallback_results = self.hybrid_search(search_query)
                if fallback_results:
                    results.extend(fallback_results)
        
        # Skip Strategy 5 (partial searches) for now to improve performance
        if time.time() - start_time > 30:  # Skip if we've been at this for 30+ seconds
            logger.info("Skipping Strategy 5 due to time constraints")
        
        # Remove duplicates and enhance scoring with deep snippet analysis
        seen_domains = set()
        unique_results = []
        for result in results:
            domain = result.get('domain', result.get('url', ''))
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                unique_results.append(result)
        
        # Use enhanced URL scorer to re-rank results based on snippet analysis
        if unique_results:
            logger.info(f"🔍 Applying enhanced URL scoring to {len(unique_results)} results")
            unique_results = self.url_scorer.rank_urls(unique_results, brand_name, brand_context)
            
            # Log top results with enhanced scores
            for i, result in enumerate(unique_results[:3]):
                logger.info(f"  #{i+1}: {result.get('domain')} - Enhanced Score: {result.get('enhanced_score', 0):.2f} - {result.get('score_explanation', '')}")
        else:
            # Fallback to original confidence sorting if no enhanced scorer
            unique_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Always suggest direct domain as an option for spirits brands
        suggested_domain = self._suggest_direct_domain(brand_name)
        if suggested_domain:
            # Check if we already found this domain
            domain_already_found = any(r.get('domain', '').lower() == suggested_domain.lower() 
                                     for r in unique_results)
            
            if not domain_already_found:
                logger.info(f"🎯 Adding domain suggestion: {suggested_domain}")
                unique_results.append({
                    'title': f"Direct Domain: {suggested_domain}",
                    'url': f"https://{suggested_domain}",
                    'domain': suggested_domain,
                    'snippet': f"Suggested official website for {brand_name}. Click to check if this domain exists.",
                    'source': 'domain_suggestion',
                    'confidence': 0.5  # Higher confidence for domain suggestions
                })
        
        logger.info(f"🔍 Intelligent search completed: {len(unique_results)} unique results found")
        return unique_results[:5]  # Return top 5 results
    
    def _suggest_direct_domain(self, brand_name: str) -> str:
        """Suggest a likely direct domain for the brand"""
        # Clean brand name for domain suggestion
        clean_name = brand_name.lower()
        clean_name = clean_name.replace(' ', '').replace('-', '').replace('_', '')
        clean_name = ''.join(c for c in clean_name if c.isalnum())
        
        # For distilleries/spirits brands, try most likely pattern
        return f"{clean_name}.com"
    
    def get_website_options(self, brand_name: str, brand_context: Optional[Dict] = None, 
                           min_confidence: float = 0.9) -> Dict[str, Any]:
        """
        Get multiple website options for user selection when confidence is low
        
        Returns:
            {
                'needs_selection': bool,  # True if user selection needed
                'top_choice': dict,       # Best option (if confidence >= min_confidence)
                'options': [dict],        # Top 3 options for user selection
                'brand_context': dict     # Brand information for decision making
            }
        """
        logger.info(f"🎯 Getting website options for: {brand_name}")
        
        # Get search results
        search_results = self.intelligent_brand_search(brand_name, brand_context)
        
        if not search_results:
            return {
                'needs_selection': False,
                'top_choice': None,
                'options': [],
                'brand_context': brand_context or {}
            }
        
        # Calculate enhanced confidence for top result using both learning and enhanced scoring
        top_result = search_results[0]
        
        # Use the enhanced score if available (from URL scorer)
        if 'enhanced_score' in top_result:
            base_confidence = top_result['enhanced_score']
        else:
            base_confidence = top_result.get('confidence', 0)
        
        # Apply learning-based enhancements on top of enhanced score
        features = {'brand_in_domain': True, 'confidence': base_confidence}
        learning_confidence = self.learning_agent.get_enhanced_confidence(
            brand_name, top_result.get('domain', ''), base_confidence, features
        )
        
        # Use the maximum of enhanced score and learning confidence
        final_confidence = max(base_confidence, learning_confidence)
        top_result['final_confidence'] = final_confidence
        
        # Log the scoring details
        if 'score_components' in top_result:
            logger.info(f"Score breakdown - Domain: {top_result['score_components'].get('domain', 0):.2f}, "
                       f"Brand: {top_result['score_components'].get('brand_match', 0):.2f}, "
                       f"Industry: {top_result['score_components'].get('industry', 0):.2f}, "
                       f"Official: {top_result['score_components'].get('official', 0):.2f}")
        
        # If confidence is high enough, return single choice
        if final_confidence >= min_confidence:
            logger.info(f"✅ High confidence ({final_confidence:.1%}) - auto-selecting website")
            return {
                'needs_selection': False,
                'top_choice': top_result,
                'options': [],
                'brand_context': brand_context or {}
            }
        
        # Low confidence - prepare multiple options for user selection
        logger.info(f"🤔 Low confidence ({final_confidence:.1%}) - presenting options for selection")
        
        # Deduplicate search results by domain before creating options
        seen_domains = set()
        unique_search_results = []
        for result in search_results:
            # Extract clean domain for deduplication
            original_url = result.get('url', '')
            if hasattr(self, 'fast_searcher') and hasattr(self.fast_searcher, 'fast_engine') and hasattr(self.fast_searcher.fast_engine, 'extract_real_url'):
                clean_url = self.fast_searcher.fast_engine.extract_real_url(original_url)
            else:
                clean_url = original_url
            
            import re
            domain_match = re.match(r'https?://([^/]+)', clean_url)
            clean_domain = domain_match.group(1).replace('www.', '').lower() if domain_match else result.get('domain', '').lower()
            
            if clean_domain and clean_domain not in seen_domains:
                seen_domains.add(clean_domain)
                unique_search_results.append(result)
        
        logger.info(f"🔄 Deduplicated from {len(search_results)} to {len(unique_search_results)} unique options")
        
        options = []
        for i, result in enumerate(unique_search_results[:3]):  # Top 3 unique options
            # Use enhanced score if available
            if 'enhanced_score' in result:
                base_conf = result['enhanced_score']
            else:
                base_conf = result.get('confidence', 0)
            
            # Apply learning enhancements
            features = {'brand_in_domain': True, 'confidence': base_conf}
            learning_conf = self.learning_agent.get_enhanced_confidence(
                brand_name, result.get('domain', ''), base_conf, features
            )
            
            final_conf = max(base_conf, learning_conf)
            
            # Build reasoning with enhanced scoring explanation
            reasoning = self._get_selection_reasoning(result, brand_context)
            if 'score_explanation' in result:
                reasoning = f"{result['score_explanation']} • {reasoning}"
            
            # Extract real URL if it's a Bing redirect
            original_url = result.get('url', '')
            if hasattr(self, 'fast_searcher') and hasattr(self.fast_searcher, 'fast_engine') and hasattr(self.fast_searcher.fast_engine, 'extract_real_url'):
                clean_url = self.fast_searcher.fast_engine.extract_real_url(original_url)
            else:
                clean_url = original_url
            
            # Extract domain from clean URL
            import re
            domain_match = re.match(r'https?://([^/]+)', clean_url)
            clean_domain = domain_match.group(1).replace('www.', '') if domain_match else result.get('domain')
            
            option = {
                'rank': i + 1,
                'url': clean_url,
                'domain': clean_domain,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'base_confidence': base_conf,
                'enhanced_confidence': learning_conf,
                'final_confidence': final_conf,
                'source': result.get('source', ''),
                'reasoning': reasoning,
                'score_components': result.get('score_components', {})
            }
            options.append(option)
        
        return {
            'needs_selection': True,
            'top_choice': None,
            'options': options,
            'brand_context': brand_context or {},
            'selection_timeout': 300  # 5 minutes to make selection
        }
    
    def _get_selection_reasoning(self, result: Dict, brand_context: Dict) -> str:
        """Generate reasoning text to help user make selection"""
        reasons = []
        
        domain = result.get('domain', '')
        title = result.get('title', '')
        snippet = result.get('snippet', '')
        
        # Domain analysis
        if any(term in domain.lower() for term in ['distillery', 'brewery', 'winery', 'spirits']):
            reasons.append("🥃 Domain suggests alcohol industry")
        
        # Title analysis
        if any(term in title.lower() for term in ['distillery', 'brewery', 'spirits', 'whiskey', 'wine']):
            reasons.append("🏭 Title mentions alcohol production")
        
        # Context matching
        if brand_context:
            class_types = brand_context.get('class_types', [])
            if class_types:
                for class_type in class_types:
                    if 'whiskey' in class_type.lower() and 'whiskey' in snippet.lower():
                        reasons.append("🥃 Matches whiskey context")
                    elif 'wine' in class_type.lower() and 'wine' in snippet.lower():
                        reasons.append("🍷 Matches wine context")
                    elif 'beer' in class_type.lower() and any(term in snippet.lower() for term in ['beer', 'brewery']):
                        reasons.append("🍺 Matches beer context")
        
        # Official website indicators
        if any(term in snippet.lower() for term in ['official', 'homepage', 'welcome to']):
            reasons.append("🌐 Appears to be official website")
        
        # Commercial indicators
        if any(term in snippet.lower() for term in ['buy', 'shop', 'store', 'purchase']):
            reasons.append("🛒 Commercial/retail site")
        
        return " • ".join(reasons) if reasons else "ℹ️ General information about brand"

    def hybrid_search(self, query: str, service: str = 'bing') -> List[Dict]:
        """
        Hybrid search: Automatically chooses fast or full protection mode
        - Development: Fast mode with minimal delays (< 2 seconds)
        - Production: Full anti-detection with browser automation
        """
        try:
            if self.use_fast_mode:
                logger.info(f"🚀 Using FAST search for: {query}")
                search_result = self.fast_searcher.search(query, force_fast=True)
                results = search_result.get('results', [])
                search_time = search_result.get('search_time', 0)
                
                if results:
                    logger.info(f"✅ Fast search found {len(results)} results in {search_time:.1f}s")
                    return results
                else:
                    logger.warning(f"Fast search returned no results for: {query}")
                    # Try fallback to safe search
                    logger.info("Falling back to safe search...")
                    return self.searcher.safe_search(query, service)
            else:
                logger.info(f"Using production search system for: {query}")
                results = self.browser_searcher.safe_search(query, service='bing')
                if results:
                    logger.info(f"Production search found {len(results)} high-quality results for: {query}")
                    return results
                else:
                    logger.warning(f"Production search returned no results for: {query}")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Final fallback to safe search
            try:
                logger.info("Using fallback safe search...")
                return self.searcher.safe_search(query, service)
            except:
                pass
        
        return []
    
    def get_search_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive search system statistics for monitoring
        """
        try:
            if self.use_fast_mode:
                return {
                    'mode': 'fast_search',
                    'environment': self.environment,
                    'cache_enabled': True,
                    'avg_response_time': '<2s',
                    'status': 'optimized_for_development'
                }
            elif self.browser_searcher:
                return self.browser_searcher.get_stats()
            else:
                return {'mode': 'safe_search', 'status': 'fallback'}
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}
    
    def load_results(self):
        """Load previous enrichment results"""
        try:
            with open(self.results_file, 'r') as f:
                self.results = json.load(f)
        except:
            self.results = {}
    
    def save_results(self):
        """Save enrichment results"""
        try:
            os.makedirs('data', exist_ok=True)
            with open(self.results_file, 'w') as f:
                json.dump(self.results, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def enrich_brand_with_context(self, brand_name: str, class_type: Optional[str] = None,
                                  brand_context: Optional[Dict] = None, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Complete enrichment pipeline with brand context for intelligent search
        """
        logger.info(f"🎯 Starting enrichment for: {brand_name}")
        
        # Check cache unless skipping
        if not skip_cache and brand_name in self.results:
            logger.info(f"Using cached results for {brand_name}")
            return self.results[brand_name]
        
        enrichment = {
            'brand_name': brand_name,
            'class_type': class_type,
            'timestamp': datetime.now().isoformat(),
            'founders': [],
            'website': None,
            'apollo_contacts': [],
            'linkedin_profiles': [],
            'status': 'processing',
            'confidence': 0.0
        }
        
        try:
            # Step 1: Find founders using safe search
            logger.info("Step 1: Searching for founders...")
            founders = self.discover_founders(brand_name, class_type)
            enrichment['founders'] = founders
            
            # Step 2: Find website using intelligent search with context
            logger.info("Step 2: Intelligent website search with context...")
            
            # Use provided brand context or build basic one
            if not brand_context:
                brand_context = {
                    'class_types': [class_type] if class_type else [],
                    'countries': []
                }
            
            # Use intelligent search with context
            search_results = self.intelligent_brand_search(brand_name, brand_context)
            
            # Convert results to website format
            website = None
            if search_results:
                best_result = search_results[0]  # Already sorted by confidence
                website = {
                    'url': best_result.get('url'),
                    'domain': best_result.get('domain'),
                    'confidence': best_result.get('confidence', 0.5),
                    'title': best_result.get('title', ''),
                    'description': best_result.get('snippet', ''),
                    'search_strategy': 'intelligent_context'
                }
            
            enrichment['website'] = website
            
            # Step 3: Find LinkedIn profiles
            logger.info("Step 3: Searching for LinkedIn profiles...")
            if founders:
                for founder in founders[:2]:  # Top 2 founders
                    linkedin = self.find_linkedin(founder['name'], brand_name)
                    if linkedin:
                        enrichment['linkedin_profiles'].append(linkedin)
            
            # Step 4: Search Apollo for contacts
            if self.apollo_api_key and founders:
                logger.info("Step 4: Searching Apollo.io...")
                for founder in founders[:2]:  # Top 2 founders
                    apollo_results = self.search_apollo_person(
                        founder['name'], 
                        brand_name
                    )
                    if apollo_results:
                        enrichment['apollo_contacts'].extend(apollo_results)
            
            # Calculate overall confidence
            confidence_scores = []
            if enrichment['founders']:
                confidence_scores.append(0.8)
            if enrichment['website']:
                confidence_scores.append(enrichment['website'].get('confidence', 0))
            if enrichment['linkedin_profiles']:
                confidence_scores.append(0.7)
            if enrichment['apollo_contacts']:
                confidence_scores.append(0.9)
            
            enrichment['confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            enrichment['status'] = 'completed'
            
            # Cache results
            self.results[brand_name] = enrichment
            self.save_results()
            
            return enrichment
            
        except Exception as e:
            logger.error(f"Error enriching brand {brand_name}: {e}")
            enrichment['status'] = 'error'
            enrichment['error'] = str(e)
            return enrichment
    
    def enrich_brand_website_only(self, brand_name: str, class_type: Optional[str] = None, 
                                  skip_cache: bool = False) -> Dict[str, Any]:
        """
        Website-only enrichment pipeline (faster, no founder search timeouts)
        """
        logger.info(f"🌐 Starting WEBSITE-ONLY enrichment for: {brand_name}")
        
        # Check cache unless skipping
        if not skip_cache and brand_name in self.results:
            cached = self.results[brand_name]
            if cached.get('website'):  # If we have website data, return it
                logger.info(f"Using cached website results for {brand_name}")
                return {
                    'brand_name': brand_name,
                    'class_type': class_type,
                    'timestamp': datetime.now().isoformat(),
                    'founders': [],  # Empty for website-only mode
                    'website': cached['website'],
                    'apollo_contacts': [],  # Empty for website-only mode
                    'linkedin_profiles': [],  # Empty for website-only mode
                    'status': 'website_only',
                    'confidence': cached['website'].get('confidence', 0.0)
                }
        
        enrichment = {
            'brand_name': brand_name,
            'class_type': class_type,
            'timestamp': datetime.now().isoformat(),
            'founders': [],  # Skip founder search
            'website': None,
            'apollo_contacts': [],  # Skip Apollo search
            'linkedin_profiles': [],  # Skip LinkedIn search
            'status': 'website_only_processing',
            'confidence': 0.0
        }
        
        try:
            # WEBSITE-ONLY: Skip founder search, go directly to website search
            logger.info("🌐 WEBSITE-ONLY MODE: Skipping founder search to avoid timeouts")
            
            # Website Search: Find website using intelligent search with context
            logger.info("Step 1: Intelligent website search...")
            
            # Build brand context for intelligent search
            brand_context = {
                'class_types': [class_type] if class_type else [],
                'countries': []
            }
            
            # Check if Flask app provided context
            if hasattr(self, '_temp_brand_context') and self._temp_brand_context:
                brand_context.update(self._temp_brand_context)
                logger.info(f"Using Flask-provided context: {brand_context}")
            
            # Enhance context with producer information if available
            if hasattr(self, '_temp_producer_context') and self._temp_producer_context:
                brand_context['producers'] = self._temp_producer_context
                logger.info(f"Enhanced context with producer info: {len(self._temp_producer_context)} producers")
            
            # Use intelligent search with context
            search_results = self.intelligent_brand_search(brand_name, brand_context)
            
            # Process website results (same logic as full enrichment)
            website = self._process_website_results(search_results, brand_name)
            enrichment['website'] = website
            
            if website:
                enrichment['confidence'] = website.get('confidence', 0.0)
                enrichment['status'] = 'website_found'
                logger.info(f"✅ Website found: {website.get('url')} (confidence: {website.get('confidence', 0):.2f})")
            else:
                enrichment['status'] = 'no_website_found'
                logger.info("❌ No suitable website found")
            
            # Save results
            self.results[brand_name] = enrichment
            self.save_results()
            
            return enrichment
            
        except Exception as e:
            logger.error(f"Website-only enrichment failed for {brand_name}: {e}")
            enrichment['status'] = 'error'
            enrichment['error'] = str(e)
            return enrichment

    def _process_website_results(self, search_results: List[Dict], brand_name: str) -> Optional[Dict]:
        """
        Process search results to extract the best website match
        Extracted from enrich_brand for reuse in website-only mode
        """
        website = None
        if search_results:
            for result in search_results:
                title = result.get('title', '').lower()
                url = result.get('url', '').lower()
                
                # Skip Wikipedia, general info sites, and unrelated content
                skip_patterns = [
                    'wikipedia', 'wiki', 'century', 'history', '13th century',
                    'medieval', 'middle ages', 'historical', 'facts about',
                    'events in', 'what happened in', 'archives', 'timeline',
                    'encyclopedia', 'biographical', 'birth', 'death'
                ]
                
                # Check if this is actually about the brand (should contain brand name + alcohol terms)
                alcohol_terms = ['whiskey', 'whisky', 'bourbon', 'distillery', 'spirits', 
                               'brewery', 'wine', 'vodka', 'rum', 'gin', 'tequila', 
                               'liqueur', 'alcohol', 'beverage', 'drinks']
                
                # Enhanced filtering: Skip historical/encyclopedia content OR non-alcohol content
                is_historical = any(skip in title for skip in skip_patterns)
                is_alcohol_related = any(alcohol in title for alcohol in alcohol_terms)
                has_brand_name = brand_name.lower() in title
                
                # Skip if it's historical content (regardless of brand name match)
                if is_historical:
                    logger.info(f"Skipping historical/encyclopedia result: {title}")
                    continue
                
                # Skip if it doesn't contain brand name AND isn't alcohol-related
                if not has_brand_name and not is_alcohol_related:
                    logger.info(f"Skipping irrelevant result: {title}")
                    continue
                
                # Extract domain properly, handling Bing redirects
                try:
                    from urllib.parse import urlparse
                    import base64
                    
                    original_url = result.get('url', '')
                    actual_url = original_url
                    
                    # Handle Bing redirect URLs with base64 encoding
                    if 'bing.com/ck/a' in original_url and 'u=a1' in original_url:
                        try:
                            # Extract base64 encoded URL (skip 'a1' prefix)
                            parts = original_url.split('u=a1')
                            if len(parts) > 1:
                                encoded_part = parts[1].split('&')[0]  # This is the base64 part without 'a1'
                                # Add padding if needed for base64 decoding
                                encoded_part += '=' * (4 - len(encoded_part) % 4)
                                decoded_bytes = base64.b64decode(encoded_part)
                                actual_url = decoded_bytes.decode('utf-8')
                                logger.info(f"Decoded Bing URL: {actual_url}")
                        except Exception as e:
                            logger.debug(f"Failed to decode Bing URL: {e}")
                            # Fall back to original URL
                            pass
                    
                    parsed = urlparse(actual_url if actual_url.startswith('http') else f'http://{actual_url}')
                    domain = parsed.netloc.replace('www.', '')
                    
                    # Additional filtering after URL decoding
                    historical_domains = [
                        'onthisday.com', 'history.com', 'ohmyfacts.com', 
                        'eventshistory.com', 'wikipedia.org', 'bing.com',
                        'timeanddate.com', 'thisdayinhistory.com',
                        'britannica.com', 'famousbirthdays.com'
                    ]
                    
                    # Check if domain or URL path contains historical indicators
                    is_historical_domain = any(hist_domain in domain for hist_domain in historical_domains)
                    is_historical_path = any(hist_term in actual_url.lower() for hist_term in 
                                           ['events/date', 'history', 'facts-about', 'timeline', 'archives'])
                    
                    if is_historical_domain or is_historical_path:
                        logger.info(f"Skipping historical domain/path: {domain} - {actual_url}")
                        continue
                    
                    if domain and domain not in ['wikipedia.org', 'bing.com']:
                        # Final check: Must be alcohol-related or brand-specific
                        url_lower = actual_url.lower()
                        title_lower = result.get('title', '').lower()
                        
                        alcohol_indicators = ['distillery', 'bourbon', 'whiskey', 'whisky', 'spirits', 'brewery', 'wine', 'beer', 'ale', 'lager']
                        brand_in_url = brand_name.lower() in url_lower
                        alcohol_in_content = any(alcohol in url_lower or alcohol in title_lower for alcohol in alcohol_indicators)
                        
                        if brand_in_url or alcohol_in_content:
                            website = {
                                'url': actual_url,
                                'domain': domain,
                                'confidence': result.get('confidence', 0.7),  # Higher confidence for decoded results
                                'title': result.get('title', ''),
                                'description': result.get('snippet', ''),
                                'search_strategy': 'intelligent_context'
                            }
                            logger.info(f"Selected website: {domain} - {result.get('title', '')}")
                            break
                        else:
                            logger.info(f"Skipping non-alcohol related result: {domain} - {result.get('title', '')}")
                            continue
                except Exception as e:
                    logger.debug(f"Error extracting domain: {e}")
                    continue
        
        return website

    def enrich_brand(self, brand_name: str, class_type: Optional[str] = None, 
                     skip_cache: bool = False) -> Dict[str, Any]:
        """
        Complete enrichment pipeline for a single brand
        """
        logger.info(f"🎯 Starting FULL enrichment for: {brand_name}")
        
        # Check cache unless skipping
        if not skip_cache and brand_name in self.results:
            logger.info(f"Using cached results for {brand_name}")
            return self.results[brand_name]
        
        enrichment = {
            'brand_name': brand_name,
            'class_type': class_type,
            'timestamp': datetime.now().isoformat(),
            'founders': [],
            'website': None,
            'apollo_contacts': [],
            'linkedin_profiles': [],
            'status': 'processing',
            'confidence': 0.0
        }
        
        try:
            # Step 1: Find founders using safe search
            logger.info("Step 1: Searching for founders...")
            founders = self.discover_founders(brand_name, class_type)
            enrichment['founders'] = founders
            
            # Step 2: Find website using intelligent search with context
            logger.info("Step 2: Intelligent website search...")
            
            # Build brand context for intelligent search
            brand_context = {
                'class_types': [class_type] if class_type else [],
                'countries': []
            }
            
            # Check if Flask app provided context
            if hasattr(self, '_temp_brand_context') and self._temp_brand_context:
                brand_context.update(self._temp_brand_context)
                logger.info(f"Using Flask-provided context: {brand_context}")
            
            # Enhance context with producer information if available
            if hasattr(self, '_temp_producer_context') and self._temp_producer_context:
                brand_context['producers'] = self._temp_producer_context
                logger.info(f"Enhanced context with producer info: {len(self._temp_producer_context)} producers")
            
            # Use intelligent search with context
            search_results = self.intelligent_brand_search(brand_name, brand_context)
            
            # Convert results to website format, filtering out irrelevant results
            website = None
            if search_results:
                for result in search_results:
                    title = result.get('title', '').lower()
                    url = result.get('url', '').lower()
                    
                    # Skip Wikipedia, general info sites, and unrelated content
                    skip_patterns = [
                        'wikipedia', 'wiki', 'century', 'history', '13th century',
                        'medieval', 'middle ages', 'historical', 'facts about',
                        'events in', 'what happened in', 'archives', 'timeline',
                        'encyclopedia', 'biographical', 'birth', 'death'
                    ]
                    
                    # Check if this is actually about the brand (should contain brand name + alcohol terms)
                    alcohol_terms = ['whiskey', 'whisky', 'bourbon', 'distillery', 'spirits', 
                                   'brewery', 'wine', 'vodka', 'rum', 'gin', 'tequila', 
                                   'liqueur', 'alcohol', 'beverage', 'drinks']
                    
                    # Enhanced filtering: Skip historical/encyclopedia content OR non-alcohol content
                    is_historical = any(skip in title for skip in skip_patterns)
                    is_alcohol_related = any(alcohol in title for alcohol in alcohol_terms)
                    has_brand_name = brand_name.lower() in title
                    
                    # Skip if it's historical content (regardless of brand name match)
                    if is_historical:
                        logger.info(f"Skipping historical/encyclopedia result: {title}")
                        continue
                    
                    # Skip if it doesn't contain brand name AND isn't alcohol-related
                    if not has_brand_name and not is_alcohol_related:
                        logger.info(f"Skipping irrelevant result: {title}")
                        continue
                    
                    # Extract domain properly, handling Bing redirects
                    try:
                        from urllib.parse import urlparse
                        import base64
                        
                        original_url = result.get('url', '')
                        actual_url = original_url
                        
                        # Handle Bing redirect URLs with base64 encoding
                        if 'bing.com/ck/a' in original_url and 'u=a1' in original_url:
                            try:
                                # Extract base64 encoded URL (skip 'a1' prefix)
                                parts = original_url.split('u=a1')
                                if len(parts) > 1:
                                    encoded_part = parts[1].split('&')[0]  # This is the base64 part without 'a1'
                                    # Add padding if needed for base64 decoding
                                    encoded_part += '=' * (4 - len(encoded_part) % 4)
                                    decoded_bytes = base64.b64decode(encoded_part)
                                    actual_url = decoded_bytes.decode('utf-8')
                                    logger.info(f"Decoded Bing URL: {actual_url}")
                            except Exception as e:
                                logger.debug(f"Failed to decode Bing URL: {e}")
                                # Fall back to original URL
                                pass
                        
                        parsed = urlparse(actual_url if actual_url.startswith('http') else f'http://{actual_url}')
                        domain = parsed.netloc.replace('www.', '')
                        
                        # Additional filtering after URL decoding
                        historical_domains = [
                            'onthisday.com', 'history.com', 'ohmyfacts.com', 
                            'eventshistory.com', 'wikipedia.org', 'bing.com',
                            'timeanddate.com', 'thisdayinhistory.com',
                            'britannica.com', 'famousbirthdays.com'
                        ]
                        
                        # Check if domain or URL path contains historical indicators
                        is_historical_domain = any(hist_domain in domain for hist_domain in historical_domains)
                        is_historical_path = any(hist_term in actual_url.lower() for hist_term in 
                                               ['events/date', 'history', 'facts-about', 'timeline', 'archives'])
                        
                        if is_historical_domain or is_historical_path:
                            logger.info(f"Skipping historical domain/path: {domain} - {actual_url}")
                            continue
                        
                        if domain and domain not in ['wikipedia.org', 'bing.com']:
                            # Final check: Must be alcohol-related or brand-specific
                            url_lower = actual_url.lower()
                            title_lower = result.get('title', '').lower()
                            
                            alcohol_indicators = ['distillery', 'bourbon', 'whiskey', 'whisky', 'spirits', 'brewery', 'wine', 'beer', 'ale', 'lager']
                            brand_in_url = brand_name.lower() in url_lower
                            alcohol_in_content = any(alcohol in url_lower or alcohol in title_lower for alcohol in alcohol_indicators)
                            
                            if brand_in_url or alcohol_in_content:
                                website = {
                                    'url': actual_url,
                                    'domain': domain,
                                    'confidence': result.get('confidence', 0.7),  # Higher confidence for decoded results
                                    'title': result.get('title', ''),
                                    'description': result.get('snippet', ''),
                                    'search_strategy': 'intelligent_context'
                                }
                                logger.info(f"Selected website: {domain} - {result.get('title', '')}")
                                break
                            else:
                                logger.info(f"Skipping non-alcohol related result: {domain} - {result.get('title', '')}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error extracting domain: {e}")
                        continue
            
            enrichment['website'] = website
            
            # Step 3: Find LinkedIn profiles
            logger.info("Step 3: Searching for LinkedIn profiles...")
            if founders:
                for founder in founders[:2]:  # Top 2 founders
                    linkedin = self.find_linkedin(founder['name'], brand_name)
                    if linkedin:
                        enrichment['linkedin_profiles'].append(linkedin)
            
            # Step 4: Search Apollo for contacts
            if self.apollo_api_key and founders:
                logger.info("Step 4: Searching Apollo.io...")
                for founder in founders[:2]:  # Top 2 founders
                    apollo_results = self.search_apollo_person(
                        founder['name'], 
                        brand_name
                    )
                    if apollo_results:
                        enrichment['apollo_contacts'].extend(apollo_results)
            
            # Calculate overall confidence
            enrichment['confidence'] = self.calculate_confidence(enrichment)
            enrichment['status'] = 'complete'
            
        except Exception as e:
            logger.error(f"Error enriching {brand_name}: {e}")
            enrichment['status'] = 'error'
            enrichment['error'] = str(e)
        
        # Save results
        self.results[brand_name] = enrichment
        self.save_results()
        
        return enrichment
    
    def discover_founders(self, brand_name: str, class_type: Optional[str] = None) -> List[Dict]:
        """
        Discover founder/owner names using safe search
        Improved for brands with numbers like "1220 SPIRITS"
        """
        founders = []
        seen_names = set()
        
        # Build search queries - start with exact matches for better results
        # Keep original case for exact searches, then try proper case
        brand_original = brand_name.strip()
        brand_proper = ' '.join([word.capitalize() for word in brand_name.split()])
        
        # Priority sequence: exact quotes first (like user's successful Google search)
        queries = [
            f'"{brand_original}"',  # Exact match first - "1220 SPIRITS"
            f'"{brand_proper}"',    # Exact proper case - "1220 Spirits"
            f'{brand_proper}',       # Simple proper case - 1220 Spirits
            f'{brand_original}',     # Original case - 1220 SPIRITS
            f'"{brand_original}" founder',
            f'"{brand_proper}" founder',
            f'{brand_proper} distillery',
            f'{brand_proper} founder',
            f'who founded {brand_proper}',
            f'{brand_proper} CEO president',
        ]
        
        # Add industry-specific queries
        if class_type:
            if 'whisk' in class_type.lower() or 'bourbon' in class_type.lower():
                queries.append(f'"{brand_name}" master distiller')
            elif 'wine' in class_type.lower():
                queries.append(f'"{brand_name}" winemaker vintner')
            elif 'beer' in class_type.lower():
                queries.append(f'"{brand_name}" brewmaster')
        
        # Search with each query using multiple engines
        all_results = []
        for i, query in enumerate(queries):
            # Use different engines for different query types
            if i < 4:  # First 4 exact/simple queries - use hybrid search
                # Try hybrid search (HTTP Bing first, browser Bing fallback)
                results = self.hybrid_search(query, service='bing')
                all_results.extend(results)
            else:
                # Use hybrid search for complex queries too
                results = self.hybrid_search(query, service='bing')
                all_results.extend(results)
            
            # Stop if we have enough results
            if len(all_results) >= 15:
                break
        
        # Extract founder names from results
        for result in all_results:
            text = f"{result.get('title', '')} {result.get('snippet', '')}"
            
            # Try each pattern
            for pattern in self.founder_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Clean and validate name
                    name = self.clean_name(match)
                    
                    if name and name.lower() not in seen_names:
                        if self.is_valid_name(name):
                            seen_names.add(name.lower())
                            founders.append({
                                'name': name,
                                'source': result.get('url', 'search'),
                                'context': text[:200],
                                'confidence': 0.7
                            })
        
        # Sort by confidence and deduplicate
        founders = self.consolidate_founders(founders)
        
        return founders[:5]  # Return top 5
    
    def find_website(self, brand_name: str) -> Optional[Dict]:
        """
        Find official website for brand with agentic learning improvements
        """
        # Keep both original and proper case for better search results
        brand_original = brand_name.strip()
        brand_proper = ' '.join([word.capitalize() for word in brand_name.split()])
        
        # Get enhanced search queries from learning agent
        suggested_queries = self.learning_agent.suggest_search_improvements(brand_name)
        
        # Combine suggested queries with base queries
        website_queries = suggested_queries + [
            f'"{brand_original}"',      # Exact original - "1220 SPIRITS"
            f'"{brand_proper}"',        # Exact proper case - "1220 Spirits"
            brand_proper,               # Simple proper case - 1220 Spirits
            brand_original,             # Original case - 1220 SPIRITS
            f'{brand_proper} distillery',
            f'"{brand_proper}" official website'
        ]
        
        # Remove duplicates while preserving order
        website_queries = list(dict.fromkeys(website_queries))
        
        results = []
        for i, query in enumerate(website_queries):
            # For exact searches, try multiple engines
            # Use hybrid search for all website finding queries
            search_results = self.hybrid_search(query, service='bing')
            results.extend(search_results)
                
            if len(results) >= 8:  # Got enough results
                break
        
        for result in results[:5]:
            url = result.get('url', '')
            
            # Get learned false positive domains from learning agent
            learned_skip_domains = self.learning_agent.knowledge_base.get('false_positive_domains', [])
            
            # Skip social media, directories, search engines, and learned false positives
            skip_domains = ['facebook', 'instagram', 'twitter', 'linkedin', 
                          'wikipedia', 'yelp', 'tripadvisor', 'google', 'bing', 
                          'yahoo', 'duckduckgo', 'amazon', 'ebay', 'pinterest'] + learned_skip_domains
            
            if url and not any(skip in url.lower() for skip in skip_domains):
                # Extract domain
                from urllib.parse import urlparse
                import base64
                
                try:
                    # Handle Bing redirect URLs with base64 encoding
                    actual_url = url
                    if 'bing.com/ck/a' in url and 'u=a1' in url:
                        try:
                            # Extract base64 encoded URL (skip 'a1' prefix)
                            parts = url.split('u=a1')
                            if len(parts) > 1:
                                encoded_part = parts[1].split('&')[0]  # This is the base64 part without 'a1'
                                # Add padding if needed for base64 decoding
                                encoded_part += '=' * (4 - len(encoded_part) % 4)
                                decoded_bytes = base64.b64decode(encoded_part)
                                actual_url = decoded_bytes.decode('utf-8')
                                logger.info(f"Decoded Bing URL in agentic search: {actual_url}")
                        except Exception as e:
                            logger.debug(f"Failed to decode Bing URL in agentic search: {e}")
                            # Fall back to original URL
                            pass
                    
                    parsed = urlparse(actual_url if actual_url.startswith('http') else f'http://{actual_url}')
                    domain = parsed.netloc.replace('www.', '')
                    
                    if domain:
                        # Calculate base confidence using existing method (use actual URL, not redirect)
                        base_confidence = self._calculate_website_confidence_legacy(brand_name, actual_url, domain)
                        
                        # Get enhanced confidence from learning agent
                        features = {
                            'brand_in_domain': brand_name.lower().replace(' ', '') in domain.lower(),
                            'industry_keyword': any(keyword in domain.lower() 
                                                  for keyword in self.learning_agent.knowledge_base.get('industry_keywords', [])),
                            'search_query_used': query,
                            'result_position': len([r for r in results if r.get('url', '') == url]) + 1
                        }
                        
                        enhanced_confidence = self.learning_agent.get_enhanced_confidence(
                            brand_name, domain, base_confidence, features
                        )
                        
                        return {
                            'domain': domain,
                            'url': actual_url if actual_url.startswith('http') else f"https://{domain}",
                            'source': 'agentic_search',
                            'base_confidence': base_confidence,
                            'enhanced_confidence': enhanced_confidence,
                            'features': features
                        }
                except:
                    continue
        
        return None
    
    def find_linkedin(self, person_name: str, brand_name: str) -> Optional[Dict]:
        """
        Find LinkedIn profile for a person
        """
        query = f'site:linkedin.com/in "{person_name}" "{brand_name}"'
        results = self.hybrid_search(query, service='bing')
        
        for result in results[:3]:
            url = result.get('url', '')
            if 'linkedin.com/in/' in url:
                return {
                    'name': person_name,
                    'url': url,
                    'title': self.extract_title_from_snippet(result.get('snippet', '')),
                    'source': 'linkedin_search'
                }
        
        return None
    
    def search_apollo_person(self, person_name: str, company_hint: str) -> List[Dict]:
        """
        Search Apollo.io by person name
        """
        if not self.apollo_api_key:
            logger.warning("Apollo API key not configured")
            return []
        
        try:
            url = "https://api.apollo.io/v1/mixed_people/search"
            
            headers = {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json',
                'X-Api-Key': self.apollo_api_key
            }
            
            data = {
                "q_person_name": person_name,
                "q_organization_name": company_hint,
                "page": 1,
                "per_page": 5
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                contacts = []
                
                for person in result.get('people', []):
                    # Check if title matches our criteria
                    title = (person.get('title') or '').lower()
                    is_relevant = any(exec_title in title for exec_title in self.executive_titles)
                    
                    if is_relevant or not person.get('title'):  # Include if no title (might be owner)
                        contacts.append({
                            'name': person.get('name'),
                            'title': person.get('title'),
                            'company': person.get('organization', {}).get('name'),
                            'email': person.get('email'),
                            'email_status': person.get('email_status'),
                            # Phone numbers removed to save API credits (costs 2-3x more than email)
                            # 'phone': person.get('phone_numbers', []),
                            'linkedin': person.get('linkedin_url'),
                            'location': f"{person.get('city', '')}, {person.get('state', '')}".strip(', '),
                            'source': 'apollo',
                            'relevance': 'high' if is_relevant else 'medium'
                        })
                
                return contacts
                
        except Exception as e:
            logger.error(f"Apollo API error: {e}")
            
        return []
    
    def clean_name(self, name: str) -> str:
        """
        Clean and standardize a person's name
        """
        if isinstance(name, tuple):
            name = ' '.join(name)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common suffixes
        suffixes = ['Jr', 'Sr', 'III', 'II', 'PhD', 'MD']
        for suffix in suffixes:
            name = name.replace(f' {suffix}', '').replace(f', {suffix}', '')
        
        # Proper capitalization
        words = name.split()
        cleaned = []
        for word in words:
            if word.isupper() or word.islower():
                word = word.capitalize()
            cleaned.append(word)
        
        return ' '.join(cleaned)
    
    def is_valid_name(self, name: str) -> bool:
        """
        Validate if string is likely a person's name
        """
        if not name or len(name) < 3:
            return False
        
        words = name.split()
        if len(words) < 2 or len(words) > 4:
            return False
        
        # Check for company words
        company_words = ['Inc', 'LLC', 'Ltd', 'Company', 'Corporation', 
                        'Distillery', 'Winery', 'Brewery', 'Group']
        if any(word in name for word in company_words):
            return False
        
        # Must have at least one capital letter
        if not any(c.isupper() for c in name):
            return False
        
        return True
    
    def extract_title_from_snippet(self, snippet: str) -> str:
        """
        Extract job title from search snippet
        """
        snippet_lower = snippet.lower()
        
        for title in self.executive_titles:
            if title in snippet_lower:
                return title.title()
        
        return "Executive"
    
    def consolidate_founders(self, founders: List[Dict]) -> List[Dict]:
        """
        Consolidate and rank founder information
        """
        consolidated = {}
        
        for founder in founders:
            name_key = founder['name'].lower()
            
            if name_key not in consolidated:
                consolidated[name_key] = founder
                consolidated[name_key]['sources'] = [founder.get('source', '')]
                consolidated[name_key]['mention_count'] = 1
            else:
                # Increase confidence with multiple mentions
                consolidated[name_key]['confidence'] = min(
                    1.0, 
                    consolidated[name_key]['confidence'] + 0.1
                )
                consolidated[name_key]['sources'].append(founder.get('source', ''))
                consolidated[name_key]['mention_count'] += 1
        
        # Sort by confidence and mention count
        final_list = list(consolidated.values())
        final_list.sort(
            key=lambda x: (x['confidence'], x['mention_count']), 
            reverse=True
        )
        
        return final_list
    
    def calculate_confidence(self, enrichment: Dict) -> float:
        """
        Calculate overall enrichment confidence
        """
        confidence = 0.0
        
        # Founders found
        if enrichment['founders']:
            confidence += 0.3
            if len(enrichment['founders']) > 1:
                confidence += 0.1
        
        # Website found
        if enrichment['website']:
            confidence += 0.2
        
        # LinkedIn profiles found
        if enrichment['linkedin_profiles']:
            confidence += 0.2
        
        # Apollo contacts found
        if enrichment['apollo_contacts']:
            confidence += 0.3
            # Bonus for verified emails
            verified_emails = [c for c in enrichment['apollo_contacts'] 
                             if c.get('email_status') == 'verified']
            if verified_emails:
                confidence += 0.1
        
        return min(1.0, confidence)
    
    def _calculate_website_confidence_legacy(self, brand_name: str, website_url: str, domain: str) -> float:
        """Legacy website confidence calculation for backward compatibility"""
        confidence = 0.0
        brand_lower = brand_name.lower().replace(' ', '')
        domain_lower = domain.lower()
        
        # Exact brand name in domain (highest confidence)
        if brand_lower in domain_lower or any(word in domain_lower for word in brand_lower.split()):
            confidence += 0.4
        
        # Common patterns for spirits brands
        spirit_keywords = ['spirits', 'distillery', 'whiskey', 'vodka', 'gin', 'rum', 'bourbon', 'wine', 'brewery']
        if any(keyword in domain_lower for keyword in spirit_keywords):
            confidence += 0.2
        
        # Brand name appears in multiple parts of domain
        brand_words = brand_name.lower().split()
        if len(brand_words) > 1:
            word_matches = sum(1 for word in brand_words if word in domain_lower)
            confidence += (word_matches / len(brand_words)) * 0.3
        
        # Domain structure suggests official site
        if domain_lower.count('.') == 1 and not any(sub in domain_lower for sub in ['blog', 'shop', 'store', 'news']):
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def record_website_feedback(self, brand_name: str, website_data: Dict, user_action: str, notes: str = ""):
        """Record user feedback for learning"""
        if not website_data:
            return
            
        features = website_data.get('features', {})
        features['search_terms_used'] = self.learning_agent.suggest_search_improvements(brand_name)
        
        self.learning_agent.record_user_feedback(
            brand_name=brand_name,
            domain=website_data.get('domain', ''),
            predicted_confidence=website_data.get('enhanced_confidence', website_data.get('base_confidence', 0.0)),
            user_action=user_action,
            features=features,
            metadata={'notes': notes, 'url': website_data.get('url', '')}
        )
        
        logger.info(f"Recorded learning feedback: {brand_name} -> {website_data.get('domain')} ({user_action})")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning agent"""
        return self.learning_agent.get_learning_insights()
    
    def enrich_multiple_brands(self, brand_list: List[Tuple[str, str]], 
                              max_brands: int = 10) -> Dict[str, Any]:
        """
        Enrich multiple brands with rate limiting
        """
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'brands': []
        }
        
        for brand_name, class_type in brand_list[:max_brands]:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"Processing {results['processed'] + 1}/{min(len(brand_list), max_brands)}: {brand_name}")
                
                enrichment = self.enrich_brand(brand_name, class_type)
                
                results['brands'].append(enrichment)
                results['processed'] += 1
                
                if enrichment['status'] == 'complete':
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                # Status update
                if enrichment['founders']:
                    logger.info(f"✅ Found {len(enrichment['founders'])} founders")
                if enrichment['apollo_contacts']:
                    logger.info(f"✅ Found {len(enrichment['apollo_contacts'])} Apollo contacts")
                
                # Rate limiting between brands
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error processing {brand_name}: {e}")
                results['failed'] += 1
        
        return results


def main():
    """
    Test the integrated enrichment system
    """
    # Initialize with Apollo API key (set in environment or here)
    enricher = IntegratedEnrichmentSystem(
        apollo_api_key=os.getenv('APOLLO_API_KEY')
    )
    
    print("🚀 Integrated Brand Enrichment System")
    print("=" * 50)
    
    # Test with a few brands
    test_brands = [
        ("Jack Daniels", "Whiskey"),
        ("Grey Goose", "Vodka"),
        ("Dom Perignon", "Wine")
    ]
    
    results = enricher.enrich_multiple_brands(test_brands, max_brands=3)
    
    print(f"\n📊 Summary:")
    print(f"  Processed: {results['processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    
    # Show detailed results
    for brand_result in results['brands']:
        print(f"\n🍾 {brand_result['brand_name']}:")
        print(f"  Status: {brand_result['status']}")
        print(f"  Confidence: {brand_result['confidence']:.1%}")
        
        if brand_result['founders']:
            print(f"  Founders: {', '.join([f['name'] for f in brand_result['founders']])}")
        
        if brand_result['website']:
            print(f"  Website: {brand_result['website']['domain']}")
        
        if brand_result['apollo_contacts']:
            print(f"  Apollo Contacts: {len(brand_result['apollo_contacts'])}")
            for contact in brand_result['apollo_contacts'][:2]:
                print(f"    - {contact['name']} ({contact.get('title', 'N/A')})")
                if contact.get('email'):
                    print(f"      Email: {contact['email']}")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()