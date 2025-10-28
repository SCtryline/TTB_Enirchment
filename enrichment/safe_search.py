#!/usr/bin/env python3
"""
Safe Search System with IP Protection and Anti-Detection
Implements multiple layers of protection to avoid detection and IP blocking
"""

import json
import time
import random
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import hashlib
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SafeSearchSystem:
    """
    Protected search system with multiple anti-detection measures
    """
    
    def __init__(self, use_proxies: bool = True, use_tor: bool = False):
        self.use_proxies = use_proxies
        self.use_tor = use_tor
        
        # Rate limiting configuration
        self.rate_limits = {
            'google': {'requests_per_hour': 20, 'delay_range': (15, 45)},
            'duckduckgo': {'requests_per_hour': 60, 'delay_range': (5, 15)},
            'bing': {'requests_per_hour': 40, 'delay_range': (10, 20)},
            'searx': {'requests_per_hour': 100, 'delay_range': (3, 8)},
            'default': {'requests_per_hour': 30, 'delay_range': (10, 30)}
        }
        
        # Request tracking for rate limiting
        self.request_history = {
            'google': [],
            'duckduckgo': [],
            'bing': [],
            'searx': []
        }
        
        # User agent rotation pool
        self.user_agents = [
            # Chrome variants
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            # Firefox variants
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            
            # Safari variants
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            
            # Edge variants
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            
            # Mobile variants (occasional mobile searches look natural)
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        ]
        
        # Free proxy services (these are examples - you'd want to use reliable services)
        self.proxy_providers = [
            # Free proxy APIs (limited but useful for basic protection)
            'https://www.proxy-list.download/api/v1/get?type=https',
            'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=US',
        ]
        
        # Initialize proxy pool
        self.proxy_pool = []
        self.current_proxy_index = 0
        
        # Session configuration with retry strategy
        self.session = self._create_session()
        
        # SearX instances (privacy-focused metasearch engine)
        self.searx_instances = [
            'https://searx.be',
            'https://searx.info',
            'https://searx.ninja',
            'https://search.privacytools.io',
            'https://searx.tiekoetter.com'
        ]
        
        # Cache for reducing repeated searches
        self.cache_file = 'data/safe_search_cache.json'
        self.load_cache()
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry strategy and timeout
        """
        session = requests.Session()
        
        # Retry strategy
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default timeout
        session.request = lambda *args, **kwargs: requests.Session.request(
            session, 
            *args, 
            timeout=kwargs.pop('timeout', 10),
            **kwargs
        )
        
        return session
    
    def load_cache(self):
        """Load search cache"""
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except:
            self.cache = {}
    
    def save_cache(self):
        """Save search cache"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def setup_tor(self) -> bool:
        """
        Setup Tor proxy if requested (requires Tor to be installed)
        """
        if not self.use_tor:
            return False
        
        try:
            # Tor default SOCKS proxy
            tor_proxy = {
                'http': 'socks5://127.0.0.1:9050',
                'https': 'socks5://127.0.0.1:9050'
            }
            
            # Test Tor connection
            test_url = 'http://httpbin.org/ip'
            response = requests.get(test_url, proxies=tor_proxy, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Tor connected. IP: {response.json().get('origin')}")
                return True
                
        except Exception as e:
            logger.warning(f"Tor not available: {e}")
            
        return False
    
    def fetch_proxies(self) -> List[str]:
        """
        Fetch free proxy list (use with caution - free proxies are unreliable)
        For production, use paid proxy services like:
        - ProxyMesh
        - Bright Data (formerly Luminati)
        - Smartproxy
        - Oxylabs
        """
        proxies = []
        
        # This is a placeholder - in production, use reliable proxy services
        logger.warning("Using free proxies is not recommended for production. Consider paid services.")
        
        # Example of fetching from free proxy list
        try:
            response = requests.get(
                'https://www.proxy-list.download/api/v1/get?type=https',
                timeout=10
            )
            if response.status_code == 200:
                proxy_list = response.text.strip().split('\n')
                for proxy in proxy_list[:10]:  # Limit to 10 proxies
                    proxies.append(f"http://{proxy}")
        except Exception as e:
            logger.error(f"Error fetching proxies: {e}")
        
        return proxies
    
    def get_random_headers(self) -> Dict[str, str]:
        """
        Generate random realistic headers
        """
        user_agent = random.choice(self.user_agents)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'en-GB,en;q=0.9',
                'en-US,en;q=0.8,es;q=0.6',
                'en-US,en;q=0.9,fr;q=0.8'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': random.choice(['1', None]),  # Sometimes include DNT
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Remove None values
        headers = {k: v for k, v in headers.items() if v is not None}
        
        # Add referer occasionally (looks more natural)
        if random.random() > 0.5:
            headers['Referer'] = random.choice([
                'https://www.google.com/',
                'https://duckduckgo.com/',
                'https://www.bing.com/'
            ])
        
        return headers
    
    def check_rate_limit(self, service: str) -> bool:
        """
        Check if we're within rate limits for a service
        """
        limits = self.rate_limits.get(service, self.rate_limits['default'])
        max_requests = limits['requests_per_hour']
        
        # Clean old requests (older than 1 hour)
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        if service in self.request_history:
            self.request_history[service] = [
                req_time for req_time in self.request_history[service]
                if req_time > cutoff_time
            ]
            
            # Check if we've hit the limit
            if len(self.request_history[service]) >= max_requests:
                logger.warning(f"Rate limit reached for {service}. Waiting...")
                return False
        
        return True
    
    def add_request_to_history(self, service: str):
        """
        Track a request for rate limiting
        """
        if service not in self.request_history:
            self.request_history[service] = []
        
        self.request_history[service].append(datetime.now())
    
    def smart_delay(self, service: str):
        """
        Add intelligent delay between requests
        """
        limits = self.rate_limits.get(service, self.rate_limits['default'])
        min_delay, max_delay = limits['delay_range']
        
        # Add random delay
        delay = random.uniform(min_delay, max_delay)
        
        # Add extra delay during business hours (looks more natural)
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            delay *= 0.8  # Slightly faster during work hours
        else:
            delay *= 1.2  # Slower outside work hours
        
        # Add occasional longer delays (mimics human behavior)
        if random.random() < 0.1:  # 10% chance
            delay *= random.uniform(2, 4)
            logger.info(f"Taking a longer break ({delay:.1f}s) - mimicking human behavior")
        
        time.sleep(delay)
    
    def safe_search(self, query: str, service: str = 'duckduckgo') -> List[Dict]:
        """
        Perform a safe search with all protection measures
        """
        # Check cache first
        cache_key = hashlib.md5(f"{service}_{query}".encode()).hexdigest()
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # Check if cache is fresh (less than 7 days old)
            if 'timestamp' in cached_data:
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                if (datetime.now() - cache_time) < timedelta(days=7):
                    logger.info(f"Using cached result for: {query}")
                    return cached_data.get('results', [])
        
        # Check rate limit
        if not self.check_rate_limit(service):
            # If rate limited, try alternative service
            alt_services = ['searx', 'duckduckgo', 'bing']
            for alt in alt_services:
                if alt != service and self.check_rate_limit(alt):
                    service = alt
                    break
            else:
                # All services rate limited, wait
                time.sleep(60)
                return []
        
        # Perform search based on service
        results = []
        
        try:
            if service == 'duckduckgo':
                results = self._search_duckduckgo(query)
            elif service == 'searx':
                results = self._search_searx(query)
            elif service == 'bing':
                results = self._search_bing(query)
            else:
                results = self._search_duckduckgo(query)  # Default to DuckDuckGo
            
            # Cache results
            if results:
                self.cache[cache_key] = {
                    'results': results,
                    'timestamp': datetime.now().isoformat()
                }
                self.save_cache()
            
            # Track request
            self.add_request_to_history(service)
            
            # Add delay
            self.smart_delay(service)
            
        except Exception as e:
            logger.error(f"Search error for {service}: {e}")
        
        return results
    
    def _search_duckduckgo(self, query: str) -> List[Dict]:
        """
        Search using DuckDuckGo HTML (no API needed, privacy-focused)
        """
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = self.get_random_headers()
        
        try:
            response = self.session.get(url, headers=headers)
            
            # DuckDuckGo returns 202 (Accepted) instead of 200 - handle both
            if response.status_code in [200, 202]:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                for result in soup.select('.result__body')[:5]:
                    title = result.select_one('.result__title')
                    snippet = result.select_one('.result__snippet')
                    link = result.select_one('.result__url')
                    
                    if title and snippet:
                        results.append({
                            'title': title.get_text(strip=True),
                            'snippet': snippet.get_text(strip=True),
                            'url': link.get_text(strip=True) if link else '',
                            'source': 'duckduckgo'
                        })
                
                return results
            else:
                logger.warning(f"DuckDuckGo returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        
        return []
    
    def _search_searx(self, query: str) -> List[Dict]:
        """
        Search using SearX metasearch engine (very privacy-focused)
        """
        # Randomly select a SearX instance
        instance = random.choice(self.searx_instances)
        
        url = f"{instance}/search"
        params = {
            'q': query,
            'format': 'json',
            'engines': 'google,duckduckgo,bing',
            'pageno': 1
        }
        
        headers = self.get_random_headers()
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('results', [])[:5]:
                    results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('content', ''),
                        'url': item.get('url', ''),
                        'source': 'searx'
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"SearX search error: {e}")
        
        return []
    
    def _search_bing(self, query: str) -> List[Dict]:
        """
        Search using Bing (be very careful with rate limits)
        """
        # Note: Bing is more aggressive with blocking
        # Consider using Bing Search API (free tier available)
        
        url = "https://www.bing.com/search"
        params = {'q': query}
        headers = self.get_random_headers()
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = []
                
                for result in soup.select('.b_algo')[:5]:
                    title_elem = result.select_one('h2')
                    snippet_elem = result.select_one('.b_caption p')
                    link_elem = result.select_one('h2 a')
                    
                    if title_elem and snippet_elem:
                        results.append({
                            'title': title_elem.get_text(strip=True),
                            'snippet': snippet_elem.get_text(strip=True),
                            'url': link_elem.get('href', '') if link_elem else '',
                            'source': 'bing'
                        })
                
                return results
                
        except Exception as e:
            logger.error(f"Bing search error: {e}")
        
        return []
    
    def distributed_search(self, query: str, use_multiple: bool = True) -> List[Dict]:
        """
        Perform search across multiple engines to distribute load
        """
        if not use_multiple:
            return self.safe_search(query)
        
        all_results = []
        services = ['duckduckgo', 'searx']  # Safer services
        
        for service in services:
            results = self.safe_search(query, service)
            all_results.extend(results)
            
            # If we have enough results, stop
            if len(all_results) >= 5:
                break
        
        # Deduplicate results
        seen_urls = set()
        unique_results = []
        
        for result in all_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results[:10]


class VPNManager:
    """
    Optional VPN management for additional protection
    Requires VPN service with API support
    """
    
    def __init__(self, vpn_service: str = None):
        self.vpn_service = vpn_service
        self.supported_services = {
            'nordvpn': self._connect_nordvpn,
            'expressvpn': self._connect_expressvpn,
            'protonvpn': self._connect_protonvpn
        }
    
    def connect(self, country: str = 'US') -> bool:
        """
        Connect to VPN
        """
        if self.vpn_service in self.supported_services:
            return self.supported_services[self.vpn_service](country)
        return False
    
    def _connect_nordvpn(self, country: str) -> bool:
        """
        Connect to NordVPN (requires nordvpn CLI installed)
        """
        try:
            import subprocess
            result = subprocess.run(
                ['nordvpn', 'connect', country],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _connect_expressvpn(self, country: str) -> bool:
        """
        Connect to ExpressVPN (requires expressvpn CLI installed)
        """
        # Implementation would go here
        return False
    
    def _connect_protonvpn(self, country: str) -> bool:
        """
        Connect to ProtonVPN (requires protonvpn CLI installed)
        """
        # Implementation would go here
        return False


def main():
    """
    Test safe search system
    """
    searcher = SafeSearchSystem(use_proxies=False, use_tor=False)
    
    print("🛡️ Safe Search System Test")
    print("=" * 50)
    
    test_queries = [
        "Jack Daniels whiskey founder",
        "Grey Goose vodka official website",
        "Patron tequila CEO"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Searching: {query}")
        
        # Use distributed search for safety
        results = searcher.distributed_search(query, use_multiple=True)
        
        if results:
            print(f"  ✓ Found {len(results)} results")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result['title'][:60]}...")
                print(f"     Source: {result['source']}")
        else:
            print("  ✗ No results found")
    
    print("\n✅ Safe search test complete!")
    print("\n⚠️ Important Reminders:")
    print("  - Always use rate limiting")
    print("  - Rotate user agents")
    print("  - Consider using paid proxies for production")
    print("  - Respect robots.txt")
    print("  - Cache results to minimize requests")


if __name__ == "__main__":
    main()