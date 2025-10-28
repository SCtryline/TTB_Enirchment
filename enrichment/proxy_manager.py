#!/usr/bin/env python3
"""
Proxy Management System for IP Rotation
Handles free and paid proxy services for anti-detection
"""

import asyncio
import random
import requests
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Manages proxy rotation for IP-based anti-detection
    """
    
    def __init__(self, use_paid_proxies: bool = False):
        self.use_paid_proxies = use_paid_proxies
        self.proxy_pool = []
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.proxy_cache_file = 'data/proxy_cache.json'
        
        # For production: Replace with your paid proxy service credentials
        self.paid_proxy_configs = {
            # Example configurations (replace with real services)
            'proxymesh': {
                'endpoints': ['http://us-wa.proxymesh.com:31280'],
                'auth': ('username', 'password'),  # Replace with real credentials
            },
            'bright_data': {
                'endpoints': ['http://session-country-us.bright-data.com:33333'],
                'auth': ('username', 'password'),  # Replace with real credentials
            },
            'smartproxy': {
                'endpoints': ['http://gate.smartproxy.com:7000'],
                'auth': ('username', 'password'),  # Replace with real credentials
            }
        }
        
        # Free proxy sources (use with caution)
        self.free_proxy_apis = [
            'https://www.proxy-list.download/api/v1/get?type=https&anon=elite&country=US',
            'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=US&anon=elite',
        ]
    
    def load_proxy_cache(self) -> List[str]:
        """Load cached proxies"""
        try:
            with open(self.proxy_cache_file, 'r') as f:
                data = json.load(f)
                if data.get('timestamp'):
                    cache_time = datetime.fromisoformat(data['timestamp'])
                    if (datetime.now() - cache_time) < timedelta(hours=1):  # Cache for 1 hour
                        return data.get('proxies', [])
        except:
            pass
        return []
    
    def save_proxy_cache(self, proxies: List[str]):
        """Save proxies to cache"""
        try:
            import os
            os.makedirs(os.path.dirname(self.proxy_cache_file), exist_ok=True)
            with open(self.proxy_cache_file, 'w') as f:
                json.dump({
                    'proxies': proxies,
                    'timestamp': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Error saving proxy cache: {e}")
    
    def get_paid_proxies(self) -> List[Dict[str, str]]:
        """
        Get paid proxy configurations
        NOTE: Replace with real credentials for production use
        """
        if not self.use_paid_proxies:
            return []
        
        proxies = []
        for service, config in self.paid_proxy_configs.items():
            for endpoint in config['endpoints']:
                proxies.append({
                    'http': endpoint,
                    'https': endpoint,
                    'auth': config['auth'],
                    'service': service
                })
        
        logger.info(f"Loaded {len(proxies)} paid proxy configurations")
        return proxies
    
    def fetch_free_proxies(self) -> List[str]:
        """
        Fetch free proxies (use with extreme caution)
        Free proxies are unreliable and potentially unsafe
        """
        if self.use_paid_proxies:
            return []  # Don't mix free and paid
        
        # Check cache first
        cached_proxies = self.load_proxy_cache()
        if cached_proxies:
            logger.info(f"Using {len(cached_proxies)} cached free proxies")
            return cached_proxies
        
        proxies = []
        
        for api_url in self.free_proxy_apis:
            try:
                logger.info(f"Fetching proxies from: {api_url}")
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    if 'proxyscrape' in api_url:
                        # ProxyScrape format
                        proxy_list = response.text.strip().split('\n')
                        for proxy in proxy_list[:5]:  # Limit to 5 per source
                            if ':' in proxy:
                                proxies.append(f"http://{proxy.strip()}")
                    else:
                        # Other formats
                        proxy_list = response.text.strip().split('\n')
                        for proxy in proxy_list[:5]:
                            if ':' in proxy:
                                proxies.append(f"http://{proxy.strip()}")
                                
            except Exception as e:
                logger.error(f"Error fetching from {api_url}: {e}")
                continue
        
        # Cache the proxies
        if proxies:
            self.save_proxy_cache(proxies)
            logger.info(f"Fetched {len(proxies)} free proxies")
        else:
            logger.warning("No free proxies obtained")
        
        return proxies
    
    def test_proxy(self, proxy: str) -> bool:
        """
        Test if a proxy is working
        """
        try:
            test_url = 'http://httpbin.org/ip'
            proxy_dict = {'http': proxy, 'https': proxy}
            
            response = requests.get(
                test_url, 
                proxies=proxy_dict, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Proxy {proxy} working. IP: {result.get('origin', 'unknown')}")
                return True
                
        except Exception as e:
            logger.debug(f"Proxy {proxy} failed: {e}")
            
        return False
    
    def initialize_proxy_pool(self):
        """
        Initialize the proxy pool with working proxies
        """
        all_proxies = []
        
        if self.use_paid_proxies:
            # Use paid proxies (recommended for production)
            paid_proxies = self.get_paid_proxies()
            all_proxies.extend(paid_proxies)
            logger.info("Using paid proxy services")
        else:
            # Use free proxies (for testing only)
            free_proxies = self.fetch_free_proxies()
            all_proxies.extend([{'http': p, 'https': p} for p in free_proxies])
            logger.warning("Using free proxies - not recommended for production")
        
        # Test proxies (skip for paid proxies to avoid unnecessary requests)
        working_proxies = []
        for proxy_config in all_proxies:
            if self.use_paid_proxies:
                # Assume paid proxies work
                working_proxies.append(proxy_config)
            else:
                # Test free proxies
                proxy_url = proxy_config['http']
                if proxy_url not in self.failed_proxies and self.test_proxy(proxy_url):
                    working_proxies.append(proxy_config)
        
        self.proxy_pool = working_proxies
        logger.info(f"Initialized proxy pool with {len(self.proxy_pool)} working proxies")
        
        return len(self.proxy_pool) > 0
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get the next proxy in rotation
        """
        if not self.proxy_pool:
            return None
        
        proxy = self.proxy_pool[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_pool)
        
        return proxy
    
    def mark_proxy_failed(self, proxy: Dict[str, str]):
        """
        Mark a proxy as failed and remove from pool
        """
        proxy_url = proxy.get('http', '')
        self.failed_proxies.add(proxy_url)
        
        if proxy in self.proxy_pool:
            self.proxy_pool.remove(proxy)
            logger.warning(f"Removed failed proxy: {proxy_url}")
        
        # Adjust current index if needed
        if self.current_proxy_index >= len(self.proxy_pool) and self.proxy_pool:
            self.current_proxy_index = 0
    
    def get_proxy_for_playwright(self) -> Optional[Dict[str, Any]]:
        """
        Get proxy configuration for Playwright
        """
        proxy = self.get_next_proxy()
        if not proxy:
            return None
        
        # Convert to Playwright format
        proxy_url = proxy['http']
        if '://' in proxy_url:
            protocol, rest = proxy_url.split('://', 1)
            server = rest
        else:
            server = proxy_url
        
        playwright_proxy = {
            'server': f'http://{server}',
        }
        
        # Add authentication if available
        if 'auth' in proxy:
            username, password = proxy['auth']
            playwright_proxy.update({
                'username': username,
                'password': password,
            })
        
        return playwright_proxy


def test_proxy_manager():
    """
    Test the proxy manager system
    """
    print("🌐 Testing Proxy Manager")
    print("=" * 30)
    
    # Test with free proxies (for demonstration)
    proxy_manager = ProxyManager(use_paid_proxies=False)
    
    print("🔍 Initializing proxy pool...")
    success = proxy_manager.initialize_proxy_pool()
    
    if success:
        print(f"✅ Initialized {len(proxy_manager.proxy_pool)} proxies")
        
        # Test rotation
        for i in range(3):
            proxy = proxy_manager.get_next_proxy()
            if proxy:
                print(f"   Proxy {i+1}: {proxy['http']}")
            else:
                print(f"   No more proxies available")
                break
        
        # Test Playwright format
        playwright_proxy = proxy_manager.get_proxy_for_playwright()
        if playwright_proxy:
            print(f"🎭 Playwright proxy format: {playwright_proxy}")
        
    else:
        print("❌ No working proxies found")
    
    print("\n💡 For production:")
    print("   - Use paid proxy services (ProxyMesh, Bright Data, etc.)")
    print("   - Set use_paid_proxies=True")
    print("   - Add real credentials to paid_proxy_configs")
    print("   - Never use free proxies for sensitive operations")


if __name__ == "__main__":
    test_proxy_manager()