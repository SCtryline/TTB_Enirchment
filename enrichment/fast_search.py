#!/usr/bin/env python3
"""
Fast Search Mode for Development and Testing
Provides quick search results without heavy anti-detection measures
"""

import requests
import json
import time
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import quote_plus, parse_qs, urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FastSearchEngine:
    """
    Lightweight search engine for development/testing
    - Minimal delays (0.5-1 second)
    - Simple HTTP requests (no browser automation)
    - Basic caching
    - Fast response times
    """
    
    def __init__(self, mode: str = 'development'):
        self.mode = mode
        self.cache_file = 'data/cache/fast_search_cache.json'
        self.cache = {}
        self.load_cache()
        
        # Fast rate limits for development
        self.rate_limits = {
            'development': {
                'min_delay': 0.5,  # Half second minimum
                'max_delay': 1.0,  # 1 second maximum
                'timeout': 10      # 10 second timeout
            },
            'testing': {
                'min_delay': 0.2,  # Even faster for testing
                'max_delay': 0.5,
                'timeout': 5
            },
            'production': {
                'min_delay': 2,    # Still faster than browser automation
                'max_delay': 5,
                'timeout': 30
            }
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def load_cache(self):
        """Load cache from file"""
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except:
            self.cache = {}
    
    def extract_real_url(self, url: str) -> str:
        """Extract real URL from Bing redirect URLs"""
        try:
            if 'bing.com/ck/a?' in url:
                # Parse Bing redirect URL to get real URL
                parsed = urlparse(url)
                query_params = parse_qs(parsed.fragment if parsed.fragment else parsed.query)
                
                # Look for the real URL in different parameters
                for param_name in ['u', 'url', 'q']:
                    if param_name in query_params:
                        potential_url = query_params[param_name][0]
                        # Decode hex-encoded URL
                        if potential_url.startswith('a1aHR0cHM6Ly8'):
                            import base64
                            try:
                                decoded = base64.b64decode(potential_url + '==').decode('utf-8')
                                if decoded.startswith('http'):
                                    return decoded
                            except:
                                pass
                        elif potential_url.startswith('http'):
                            return potential_url
                
                # Alternative: try to extract from URL pattern
                import re
                match = re.search(r'&u=a1([^&]+)', url)
                if match:
                    try:
                        import base64
                        encoded = match.group(1)
                        # Add padding if needed
                        while len(encoded) % 4:
                            encoded += '='
                        decoded = base64.b64decode(encoded).decode('utf-8')
                        if decoded.startswith('http'):
                            return decoded
                    except:
                        pass
            
            return url
        except Exception as e:
            logger.debug(f"Error extracting real URL from {url}: {e}")
            return url
    
    def save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_cache_key(self, query: str) -> str:
        """Generate cache key for query"""
        return hashlib.md5(query.encode()).hexdigest()
    
    def search_bing(self, query: str) -> List[Dict]:
        """Fast Bing search using HTTP requests"""
        cache_key = self.get_cache_key(query)
        
        # Check cache first
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if 'timestamp' in cache_entry:
                cache_time = datetime.fromisoformat(cache_entry['timestamp'])
                if datetime.now() - cache_time < timedelta(hours=24):
                    logger.info(f"Cache hit for query: {query}")
                    return cache_entry.get('results', [])
        
        # Perform search
        encoded_query = quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded_query}"
        
        try:
            limits = self.rate_limits[self.mode]
            
            # Quick delay
            time.sleep(limits['min_delay'])
            
            response = self.session.get(url, timeout=limits['timeout'])
            
            if response.status_code == 200:
                # Simple extraction of results (basic parsing)
                results = self.parse_results(response.text, query)
                
                # Cache results
                self.cache[cache_key] = {
                    'results': results,
                    'timestamp': datetime.now().isoformat(),
                    'query': query
                }
                self.save_cache()
                
                return results
            else:
                logger.warning(f"Search returned status {response.status_code}")
                return []
                
        except requests.Timeout:
            logger.error(f"Search timed out after {limits['timeout']} seconds")
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def parse_results(self, html: str, query: str) -> List[Dict]:
        """Parse Bing search results using BeautifulSoup"""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find search result entries
            # Bing uses various classes for results
            result_divs = soup.find_all('li', class_='b_algo')
            
            for div in result_divs[:10]:  # Process top 10
                try:
                    # Extract title and URL
                    h2 = div.find('h2')
                    if not h2:
                        continue
                    
                    link = h2.find('a')
                    if not link or not link.get('href'):
                        continue
                    
                    url = link.get('href')
                    title = link.get_text(strip=True)
                    
                    # Extract real URL from Bing redirect
                    real_url = self.extract_real_url(url)
                    
                    # Extract snippet
                    snippet_div = div.find('div', class_='b_caption')
                    snippet = ''
                    if snippet_div:
                        p = snippet_div.find('p')
                        if p:
                            snippet = p.get_text(strip=True)[:200]
                    
                    # Extract domain from real URL
                    import re
                    domain_match = re.match(r'https?://([^/]+)', real_url)
                    domain = domain_match.group(1) if domain_match else real_url
                    
                    # Calculate confidence score based on content quality
                    confidence = self.calculate_confidence(query, title, snippet, domain)
                    
                    results.append({
                        'title': title or f"Result for {query}",
                        'url': real_url,
                        'domain': domain,
                        'snippet': snippet or f"Fast search result from {domain}",
                        'source': 'fast_bing',
                        'confidence': confidence
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing result: {e}")
                    continue
            
            # If no results found with standard parsing, try simpler approach
            if not results:
                import re
                # Find all URLs that look like real websites
                url_pattern = r'href="(https?://(?!.*(?:bing|microsoft|msn))[^"]+)"'
                urls = re.findall(url_pattern, html)
                
                seen_domains = set()
                for url in urls[:10]:
                    # Extract real URL from potential redirects
                    real_url = self.extract_real_url(url)
                    domain_match = re.match(r'https?://([^/]+)', real_url)
                    if domain_match:
                        domain = domain_match.group(1)
                        if domain not in seen_domains and '.' in domain:
                            seen_domains.add(domain)
                            # Calculate confidence for simple results
                            confidence = self.calculate_confidence(query, f"Result for {query}", f"Search result from {domain}", domain)
                            
                            results.append({
                                'title': f"Result for {query}",
                                'url': real_url,
                                'domain': domain,
                                'snippet': f"Search result from {domain}",
                                'source': 'fast_bing',
                                'confidence': confidence
                            })
            
        except Exception as e:
            logger.error(f"Error parsing results: {e}")
        
        # Filter out unwanted domains and sort by confidence
        filtered_results = self.filter_domains(results)
        
        # Sort by confidence score (highest first)
        filtered_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # If we filtered too aggressively and have no results, relax filtering
        if not filtered_results and results:
            logger.warning("Aggressive filtering removed all results, keeping top result")
            # Keep the highest confidence result even if it's from a blocked domain
            results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            filtered_results = results[:1]
        
        return filtered_results[:5]  # Return top 5 results
    
    def filter_domains(self, results: List[Dict]) -> List[Dict]:
        """Filter out social media, forums, and other irrelevant domains"""
        blocked_domains = [
            'reddit.com', 'facebook.com', 'instagram.com', 'twitter.com', 
            'linkedin.com', 'wikipedia.org', 'yelp.com', 'tripadvisor.com',
            'pinterest.com', 'youtube.com', 'tiktok.com', 'snapchat.com',
            'amazon.com', 'ebay.com', 'walmart.com', 'google.com', 'bing.com'
        ]
        
        filtered = []
        for result in results:
            domain = result.get('domain', '').lower()
            
            # Check if domain contains any blocked terms
            is_blocked = any(blocked in domain for blocked in blocked_domains)
            
            if not is_blocked:
                filtered.append(result)
            else:
                logger.debug(f"Filtered out blocked domain: {domain}")
        
        return filtered
    
    def calculate_confidence(self, query: str, title: str, snippet: str, domain: str) -> float:
        """Calculate confidence score for search result quality"""
        confidence = 0.0
        
        # Clean query to get brand name
        brand_name = query.strip('"').lower()
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        domain_lower = domain.lower()
        
        # Base score for domain quality
        if any(tld in domain_lower for tld in ['.com', '.net', '.org']):
            confidence += 0.3
        
        # Brand name matching
        if brand_name in domain_lower:
            confidence += 0.4  # High score for brand in domain
        elif any(word in domain_lower for word in brand_name.split() if len(word) > 3):
            confidence += 0.2  # Partial brand match
        
        if brand_name in title_lower:
            confidence += 0.2
        elif any(word in title_lower for word in brand_name.split() if len(word) > 3):
            confidence += 0.1
        
        # Industry indicators (alcohol/spirits)
        industry_terms = ['distillery', 'brewery', 'winery', 'spirits', 'whiskey', 'vodka', 'gin', 'rum', 'wine', 'beer']
        if any(term in domain_lower for term in industry_terms):
            confidence += 0.2
        if any(term in title_lower for term in industry_terms):
            confidence += 0.1
        if any(term in snippet_lower for term in industry_terms):
            confidence += 0.1
        
        # Penalize social media and forums heavily
        bad_indicators = ['reddit', 'facebook', 'instagram', 'wikipedia', 'forum', 'discussion', 'review']
        if any(bad in domain_lower for bad in bad_indicators):
            confidence -= 0.5
        if any(bad in title_lower for bad in bad_indicators):
            confidence -= 0.3
            
        # Boost official-looking domains
        if any(term in domain_lower for term in ['official', 'www']):
            confidence += 0.1
            
        # Penalize aggregation/listing sites
        if any(term in domain_lower for term in ['list', 'directory', 'guide', 'top10', 'best']):
            confidence -= 0.2
            
        return max(0.0, min(1.0, confidence))  # Clamp between 0-1
    
    def search(self, query: str) -> Dict:
        """Main search method with timing"""
        start_time = time.time()
        
        logger.info(f"Fast searching for: {query} (mode: {self.mode})")
        
        results = self.search_bing(query)
        
        elapsed = time.time() - start_time
        
        return {
            'results': results,
            'search_time': elapsed,
            'mode': self.mode,
            'cached': self.get_cache_key(query) in self.cache,
            'timestamp': datetime.now().isoformat()
        }


class HybridSearchEngine:
    """
    Hybrid search that chooses between fast and full protection based on context
    """
    
    def __init__(self, environment: str = 'development'):
        self.environment = environment
        self.fast_engine = FastSearchEngine(mode='development' if environment == 'development' else 'production')
        self.use_fast_mode = environment in ['development', 'testing']
        
        # Import full engine only if needed
        if not self.use_fast_mode:
            from .search_engine import ProductionSearchWrapper
            self.full_engine = ProductionSearchWrapper()
        else:
            self.full_engine = None
    
    def search(self, query: str, force_fast: bool = False) -> Dict:
        """
        Perform search using appropriate engine
        
        Args:
            query: Search query
            force_fast: Force fast mode regardless of environment
        """
        if force_fast or self.use_fast_mode:
            logger.info("Using FAST search mode")
            return self.fast_engine.search(query)
        else:
            logger.info("Using FULL protection search mode")
            if self.full_engine:
                results = self.full_engine.safe_search(query)
                return {
                    'results': results,
                    'search_time': 0,  # Not tracked in full mode
                    'mode': 'full_protection',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning("Full engine not available, falling back to fast mode")
                return self.fast_engine.search(query)


# Convenience function for quick testing
def quick_search(query: str) -> List[Dict]:
    """Quick search for testing - returns results in under 2 seconds"""
    engine = FastSearchEngine(mode='testing')
    result = engine.search(query)
    return result.get('results', [])