#!/usr/bin/env python3
"""
Production-Ready Search System with Full Anti-Detection Suite
Combines all anti-detection measures for maximum reliability and stealth
"""

import asyncio
import time
import random
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from .stealth_system import EnhancedStealthSystem
from .proxy_manager import ProxyManager
from .captcha_handler import CaptchaHandler
from .human_behavior import HumanBehaviorSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionSearchSystem:
    """
    Enterprise-grade search system with comprehensive anti-detection measures
    
    Features:
    - Advanced browser fingerprint randomization
    - IP rotation via proxy management
    - Human-like behavior simulation
    - Intelligent rate limiting
    - Session management and tracking
    - Adaptive failure handling
    - Comprehensive caching system
    """
    
    def __init__(self, 
                 headless: bool = True, 
                 use_proxies: bool = False, 
                 paid_proxies: bool = False):
        
        self.headless = headless
        self.use_proxies = use_proxies
        
        # Initialize subsystems
        self.stealth_system = EnhancedStealthSystem()
        self.proxy_manager = ProxyManager(use_paid_proxies=paid_proxies) if use_proxies else None
        self.captcha_handler = CaptchaHandler()
        self.human_behavior = HumanBehaviorSimulator()
        
        # Conservative rate limiting for production
        self.rate_limits = {
            'requests_per_hour': 240,  # Ultra-aggressive: 16x faster      # Very conservative
            'min_delay': 0.5,  # Ultra-aggressive: minimal delay               # Minimum 5 seconds for user testing
            'max_delay': 3,  # Ultra-aggressive: very fast              # Maximum 15 seconds for user testing
            'burst_protection': True,     # Prevent burst requests
        }
        
        # Request tracking and analytics
        self.request_history = []
        self.success_rate = 0.0
        self.total_requests = 0
        self.successful_requests = 0
        
        # Cache system
        self.cache_file = 'data/production_search_cache.json'
        self.load_cache()
        
        # Session management
        self.session_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        self.session_start_time = datetime.now()
        self.browser = None
        self.context = None
        
        # Adaptive behavior
        self.failure_streak = 0
        self.max_failure_streak = 3
        self.last_proxy_rotation = datetime.now()
        
        # Performance monitoring
        self.performance_stats = {
            'avg_response_time': 0.0,
            'total_response_time': 0.0,
            'requests_count': 0,
        }
    
    def load_cache(self):
        """Load search cache with extended retention"""
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except:
            self.cache = {}
    
    def save_cache(self):
        """Save search cache"""
        try:
            import os
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def initialize_proxy_system(self) -> bool:
        """Initialize proxy system if enabled"""
        if not self.use_proxies or not self.proxy_manager:
            return True
        
        try:
            success = self.proxy_manager.initialize_proxy_pool()
            if success:
                logger.info("Proxy system initialized successfully")
            else:
                logger.warning("Proxy system initialization failed")
            return success
        except Exception as e:
            logger.error(f"Proxy initialization error: {e}")
            return False
    
    def should_rotate_proxy(self) -> bool:
        """Determine if proxy should be rotated"""
        if not self.use_proxies:
            return False
        
        # Rotate after failures
        if self.failure_streak >= 2:
            return True
        
        # Rotate periodically (every 30 minutes)
        time_since_rotation = datetime.now() - self.last_proxy_rotation
        if time_since_rotation > timedelta(minutes=30):
            return True
        
        # Rotate randomly (5% chance)
        if random.random() < 0.05:
            return True
        
        return False
    
    def update_performance_stats(self, response_time: float):
        """Update performance monitoring stats"""
        self.performance_stats['requests_count'] += 1
        self.performance_stats['total_response_time'] += response_time
        self.performance_stats['avg_response_time'] = (
            self.performance_stats['total_response_time'] / 
            self.performance_stats['requests_count']
        )
    
    def calculate_success_rate(self) -> float:
        """Calculate current success rate"""
        if self.total_requests == 0:
            return 100.0  # Start with optimistic assumption
        return (self.successful_requests / self.total_requests) * 100
    
    def check_rate_limit(self) -> bool:
        """Enhanced rate limiting with burst protection"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        # Clean old requests
        self.request_history = [
            req_time for req_time in self.request_history
            if req_time > cutoff_time
        ]
        
        # Check hourly limit
        if len(self.request_history) >= self.rate_limits['requests_per_hour']:
            logger.warning("Hourly rate limit reached")
            return False
        
        # Burst protection - max 3 requests in 5 minutes
        if self.rate_limits.get('burst_protection'):
            recent_cutoff = current_time - timedelta(minutes=5)
            recent_requests = [
                req_time for req_time in self.request_history
                if req_time > recent_cutoff
            ]
            if len(recent_requests) >= 10:  # Ultra-aggressive: more burst allowed
                logger.warning("Burst protection triggered")
                return False
        
        return True
    
    async def setup_browser_with_proxy(self) -> bool:
        """Setup browser with proxy if available"""
        try:
            if self.browser:
                await self.cleanup_browser()
            
            # Get proxy configuration
            proxy_config = None
            if self.use_proxies and self.proxy_manager:
                if self.should_rotate_proxy():
                    proxy_config = self.proxy_manager.get_proxy_for_playwright()
                    if proxy_config:
                        self.last_proxy_rotation = datetime.now()
                        logger.info(f"Using proxy: {proxy_config['server']}")
            
            # Setup browser with stealth and proxy
            self.browser, self.context = await self.stealth_system.setup_browser_with_stealth(
                headless=self.headless
            )
            
            # If proxy failed to work, try without proxy
            if proxy_config:
                try:
                    # Test proxy by creating a page
                    test_page = await self.context.new_page()
                    await test_page.goto('https://httpbin.org/ip', timeout=10000)
                    await test_page.close()
                    logger.info("Proxy connection verified")
                except Exception as e:
                    logger.warning(f"Proxy failed, continuing without: {e}")
                    if self.proxy_manager:
                        self.proxy_manager.mark_proxy_failed({'http': proxy_config['server']})
            
            self.stealth_system.track_session(self.session_id, 'browser_setup_with_proxy')
            logger.info(f"Production browser setup completed (session: {self.session_id})")
            return True
            
        except Exception as e:
            logger.error(f"Browser setup failed: {e}")
            self.failure_streak += 1
            return False
    
    async def cleanup_browser(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception as e:
            logger.error(f"Browser cleanup error: {e}")
    
    async def intelligent_delay(self):
        """Ultra-intelligent delay system for production"""
        # Base delay from stealth system
        base_delay = self.stealth_system.calculate_smart_delay()
        
        # Adjust based on success rate
        success_rate = self.calculate_success_rate()
        if success_rate < 50:  # Optimized: stricter threshold  # If success rate is low, slow down
            base_delay *= random.uniform(1.2, 1.8)  # Optimized: reduced penalty
            logger.info(f"Low success rate ({success_rate:.1f}%), increasing delay")
        
        # Adjust based on failure streak
        if self.failure_streak > 0:
            base_delay *= (1 + self.failure_streak * 0.3)  # Optimized: reduced penalty
            logger.info(f"Failure streak detected, increasing delay by {self.failure_streak * 50}%")
        
        # Add randomization to avoid patterns
        final_delay = base_delay * random.uniform(0.8, 1.4)
        
        # Ensure within bounds
        final_delay = max(self.rate_limits['min_delay'], 
                         min(self.rate_limits['max_delay'], final_delay))
        
        logger.info(f"Intelligent delay: {final_delay:.1f}s (base: {base_delay:.1f}s)")
        await asyncio.sleep(final_delay)
    
    async def search_bing_with_anti_detection(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced Bing search with comprehensive anti-detection measures
        """
        logger.info(f"🔍 Enhanced search for: '{query}' (anti-detection enabled)")
        
        start_time = time.time()
        results = []
        
        try:
            # Setup browser with enhanced stealth
            if not self.browser:
                await self._setup_browser_with_enhanced_stealth()
            
            # Create new page with human behavior simulation
            page = await self.context.new_page()
            
            try:
                # Simulate human behavior: arrive at Bing
                await page.goto('https://www.bing.com', wait_until='domcontentloaded')
                await self.human_behavior.simulate_page_arrival(page)
                
                # Check for immediate blocking/CAPTCHA
                initial_detection = await self.captcha_handler.detect_captcha(page)
                if initial_detection['detected']:
                    logger.warning(f"🚨 CAPTCHA detected on arrival: {initial_detection['type']}")
                    
                    # Try to handle CAPTCHA
                    captcha_result = await self.captcha_handler.handle_captcha(page, initial_detection)
                    if not captcha_result['resolved']:
                        raise Exception(f"CAPTCHA blocking search: {initial_detection['type']}")
                
                # Perform search with human behavior
                await self.human_behavior.simulate_search_behavior(page, query)
                
                # Wait for results with timeout protection
                try:
                    await page.wait_for_selector('.b_algo', timeout=30000)
                except Exception:
                    # Check if we're blocked
                    blocking_detection = await self.captcha_handler.detect_captcha(page)
                    if blocking_detection['detected']:
                        logger.warning(f"🚨 Search blocked: {blocking_detection['type']}")
                        
                        # Try to handle blocking
                        handle_result = await self.captcha_handler.handle_captcha(page, blocking_detection)
                        if handle_result['resolved']:
                            # Retry waiting for results
                            await page.wait_for_selector('.b_algo', timeout=15000)
                        else:
                            raise Exception(f"Search blocked and unresolvable: {blocking_detection['type']}")
                    else:
                        raise Exception("Search results not loading (unknown reason)")
                
                # Simulate human browsing behavior
                await self.human_behavior.simulate_result_browsing(page)
                
                # Extract results with enhanced parsing
                search_results = await page.query_selector_all('.b_algo')
                
                for i, result_element in enumerate(search_results[:max_results]):
                    try:
                        # Extract title
                        title_element = await result_element.query_selector('h2 a, .b_title a')
                        title = await title_element.text_content() if title_element else ""
                        
                        # Extract URL
                        url_element = await result_element.query_selector('h2 a, .b_title a')
                        url = await url_element.get_attribute('href') if url_element else ""
                        
                        # Extract snippet
                        snippet_element = await result_element.query_selector('.b_caption p, .b_snippet')
                        snippet = await snippet_element.text_content() if snippet_element else ""
                        
                        if title and url:
                            results.append({
                                'title': title.strip(),
                                'url': url.strip(),
                                'snippet': snippet.strip(),
                                'source': 'enhanced_bing',
                                'timestamp': datetime.now().isoformat(),
                                'session_id': self.session_id,
                                'rank': i + 1
                            })
                            
                    except Exception as e:
                        logger.debug(f"Error extracting result {i}: {e}")
                        continue
                
                # Track success
                search_time = time.time() - start_time
                logger.info(f"✅ Enhanced search completed: {len(results)} results in {search_time:.1f}s")
                
                # Update performance tracking
                self._update_success_metrics(True, search_time)
                
                return results
                
            finally:
                await page.close()
                
        except Exception as e:
            search_time = time.time() - start_time
            logger.error(f"❌ Enhanced search failed for '{query}': {e} (took {search_time:.1f}s)")
            
            # Update failure tracking
            self._update_failure_metrics()
            
            # Determine if we should fall back to different method
            if "CAPTCHA" in str(e) or "blocked" in str(e).lower():
                logger.info("🔄 CAPTCHA/blocking detected - recommending fallback to fast search")
                raise Exception(f"SEARCH_BLOCKED: {e}")
            else:
                raise e
    
    async def _setup_browser_with_enhanced_stealth(self) -> None:
        """Setup browser with maximum stealth configuration"""
        try:
            playwright = await self.stealth_system.get_playwright_instance()
            
            # Enhanced browser launch arguments
            browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-automation',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Faster loading
                '--disable-javascript-harmony-shipping',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-field-trial-config',
                '--disable-back-forward-cache',
                '--enable-automation=false',
                '--window-size=1366,768',  # Common resolution
                '--start-maximized'
            ]
            
            fingerprint = self.stealth_system.generate_fingerprint()
            
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=browser_args,
                proxy=self.stealth_system.get_proxy_config(self.proxy_manager) if self.proxy_manager else None
            )
            
            # Create context with enhanced stealth
            self.context = await self.browser.new_context(
                user_agent=fingerprint['user_agent'],
                viewport={'width': fingerprint['viewport']['width'], 'height': fingerprint['viewport']['height']},
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Add stealth scripts to all pages
            await self.context.add_init_script("""
                // Remove webdriver traces
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock chrome runtime
                window.chrome = {
                    runtime: {},
                };
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            logger.info(f"🛡️ Enhanced stealth browser setup completed (session: {self.session_id})")
            
        except Exception as e:
            logger.error(f"Enhanced browser setup failed: {e}")
            raise
    
    def _update_success_metrics(self, success: bool, response_time: float) -> None:
        """Update performance tracking metrics"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.failure_streak = 0
        else:
            self.failure_streak += 1
        
        # Update success rate
        self.success_rate = (self.successful_requests / self.total_requests) * 100
        
        # Update response time tracking
        self.performance_stats['requests_count'] += 1
        self.performance_stats['total_response_time'] += response_time
        self.performance_stats['avg_response_time'] = (
            self.performance_stats['total_response_time'] / self.performance_stats['requests_count']
        )
        
        # Log performance updates
        if self.total_requests % 5 == 0:  # Log every 5 requests
            logger.info(f"📊 Performance: {self.success_rate:.1f}% success rate, "
                       f"{self.performance_stats['avg_response_time']:.1f}s avg response time")
    
    def _update_failure_metrics(self) -> None:
        """Update failure tracking specifically"""
        self.failure_streak += 1
        
        # Log failure patterns
        if self.failure_streak >= 3:
            logger.warning(f"⚠️ High failure streak: {self.failure_streak} consecutive failures")
            
        # Trigger adaptive measures if failure rate is too high
        if self.success_rate < 30 and self.total_requests >= 10:
            logger.error(f"🚨 Critical failure rate: {self.success_rate:.1f}% - immediate fallback recommended")

    async def search_with_full_protection(self, query: str) -> List[Dict]:
        """
        Main search method with full protection suite
        """
        start_time = time.time()
        
        try:
            # Setup browser if needed
            if not self.browser:
                if not await self.setup_browser_with_proxy():
                    return []
            
            # Create new page
            page = await self.context.new_page()
            
            # Track search
            self.stealth_system.track_session(self.session_id, f'search:{query}')
            
            # Navigate with protection
            await page.goto('https://www.bing.com/', wait_until='networkidle')
            
            # Extended human behavior simulation
            await self.stealth_system.simulate_human_behavior(page)
            
            # Handle any popups or consent forms
            try:
                await asyncio.sleep(random.uniform(1, 3))
                consent_buttons = await page.locator('button:has-text("Accept"), button:has-text("Allow"), #bnp_btn_accept').all()
                for button in consent_buttons:
                    if await button.is_visible():
                        await button.click()
                        await asyncio.sleep(random.uniform(1, 2))
                        break
            except:
                pass
            
            # Perform search with natural typing
            search_input = page.locator('input[name="q"], #sb_form_q')
            await search_input.click()
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Type naturally
            for char in query:
                await search_input.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))
            
            await asyncio.sleep(random.uniform(0.5, 2.0))
            await search_input.press('Enter')
            
            # Wait for results with extended timeout
            await page.wait_for_selector('.b_algo', timeout=25000)
            
            # Simulate reading time
            await asyncio.sleep(random.uniform(3, 8))
            
            # Extract results
            results = []
            result_elements = await page.locator('.b_algo').all()
            
            for element in result_elements[:12]:  # Get more results
                try:
                    title = ""
                    snippet = ""
                    url = ""
                    
                    # Extract with multiple fallbacks
                    try:
                        title_elem = element.locator('h2')
                        if await title_elem.is_visible():
                            title = await title_elem.inner_text()
                    except:
                        pass
                    
                    try:
                        snippet_elem = element.locator('.b_caption')
                        if await snippet_elem.is_visible():
                            snippet = await snippet_elem.inner_text()
                    except:
                        pass
                    
                    try:
                        link_elem = element.locator('a').first
                        if await link_elem.is_visible():
                            href = await link_elem.get_attribute('href')
                            if href and href.startswith('http'):
                                url = href
                    except:
                        pass
                    
                    if (title.strip() or snippet.strip()) and len(title + snippet) > 10:
                        results.append({
                            'title': title.strip(),
                            'snippet': snippet.strip()[:300],  # Limit snippet length
                            'url': url.strip(),
                            'source': 'production_bing',
                            'timestamp': datetime.now().isoformat(),
                            'session_id': self.session_id
                        })
                        
                except Exception as e:
                    logger.debug(f"Error extracting result: {e}")
                    continue
            
            # Additional human behavior
            if results:
                # Sometimes scroll to see more results
                if random.random() < 0.4:
                    scroll_amount = random.randint(300, 800)
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(2, 5))
                
                # Sometimes click on a result (but immediately go back)
                if random.random() < 0.2 and len(results) > 1:
                    try:
                        result_link = page.locator('.b_algo a').first
                        await result_link.click()
                        await asyncio.sleep(random.uniform(1, 3))
                        await page.go_back()
                        await asyncio.sleep(random.uniform(1, 2))
                    except:
                        pass
            
            # Success tracking
            self.successful_requests += 1
            self.failure_streak = 0
            
            # Performance tracking
            response_time = time.time() - start_time
            self.update_performance_stats(response_time)
            
            logger.info(f"Production search found {len(results)} results for: {query} (took {response_time:.2f}s)")
            
            await page.close()
            return results
            
        except Exception as e:
            self.failure_streak += 1
            logger.error(f"Production search error: {e}")
            
            # Adaptive failure handling
            if self.failure_streak >= self.max_failure_streak:
                logger.warning("Max failure streak reached, recreating browser...")
                await self.cleanup_browser()
                self.failure_streak = 0
            
            return []
    
    async def search(self, query: str) -> List[Dict]:
        """
        Main search interface with full protection
        """
        self.total_requests += 1
        
        # Check cache first
        cache_key = hashlib.md5(f"production_{query}".encode()).hexdigest()
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if 'timestamp' in cached_data:
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                if (datetime.now() - cache_time) < timedelta(days=14):  # Extended cache
                    logger.info(f"Using cached result for: {query}")
                    return cached_data.get('results', [])
        
        # Check rate limit
        if not self.check_rate_limit():
            logger.warning("Rate limited, waiting...")
            await asyncio.sleep(10)  # Ultra-aggressive: short wait
            return []
        
        # Intelligent delay (except for first request)
        if self.request_history:
            await self.intelligent_delay()
        
        # Initialize proxy system if needed
        if self.use_proxies and not hasattr(self, '_proxy_initialized'):
            self.initialize_proxy_system()
            self._proxy_initialized = True
        
        # Execute search
        results = await self.search_with_full_protection(query)
        
        # Cache successful results
        if results:
            self.cache[cache_key] = {
                'results': results,
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'session_id': self.session_id
            }
            self.save_cache()
        
        # Track request
        self.request_history.append(datetime.now())
        
        return results
    
    def safe_search(self, query: str) -> List[Dict]:
        """Synchronous wrapper for compatibility"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.search(query))
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        session_duration = datetime.now() - self.session_start_time
        
        return {
            'session_id': self.session_id,
            'session_duration': str(session_duration),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'success_rate': f"{self.calculate_success_rate():.1f}%",
            'failure_streak': self.failure_streak,
            'avg_response_time': f"{self.performance_stats['avg_response_time']:.2f}s",
            'cache_size': len(self.cache),
            'proxy_enabled': self.use_proxies,
            'requests_this_hour': len(self.request_history),
        }
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.cleanup_browser())
        except:
            pass


# Convenience wrapper that matches existing interface
class ProductionSearchWrapper:
    """
    Drop-in replacement for existing search systems
    """
    
    def __init__(self, use_proxies: bool = False, paid_proxies: bool = False):
        self.searcher = ProductionSearchSystem(
            headless=True,
            use_proxies=use_proxies,
            paid_proxies=paid_proxies
        )
    
    def safe_search(self, query: str, service: str = 'bing') -> List[Dict]:
        """Compatible interface"""
        return self.searcher.safe_search(query)
    
    def distributed_search(self, query: str, use_multiple: bool = True) -> List[Dict]:
        """Compatible interface"""
        return self.searcher.safe_search(query)
    
    def get_cached_results(self, query: str) -> Optional[List[Dict]]:
        """Check if results are cached for this query"""
        import hashlib
        from datetime import datetime, timedelta
        
        # Create the same cache key as used in safe_search
        cache_key = hashlib.md5(f"production_{query}".encode()).hexdigest()
        
        if cache_key in self.searcher.cache:
            cached_data = self.searcher.cache[cache_key]
            if 'timestamp' in cached_data:
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                if (datetime.now() - cache_time) < timedelta(days=14):  # Extended cache
                    return cached_data.get('results', [])
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return self.searcher.get_session_stats()


async def test_production_system():
    """Test the complete production system"""
    print("🏭 Testing Production Search System")
    print("=" * 40)
    
    # Test without proxies first
    searcher = ProductionSearchSystem(
        headless=True,
        use_proxies=False,  # Set to True for proxy testing
        paid_proxies=False
    )
    
    try:
        test_queries = ['"1220 SPIRITS"', 'Jack Daniels']
        
        for query in test_queries:
            print(f"\n🔍 Testing: {query}")
            results = await searcher.search(query)
            
            if results:
                print(f"✅ Found {len(results)} results")
                print(f"   First: {results[0]['title'][:50]}...")
                
                if "1220" in query and results:
                    first_title = results[0]['title'].lower()
                    if '1220' in first_title and 'spirits' in first_title:
                        print(f"🎯 Perfect match for 1220 SPIRITS!")
            else:
                print(f"❌ No results found")
        
        # Show statistics
        stats = searcher.get_session_stats()
        print(f"\n📊 Session Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
    finally:
        await searcher.cleanup_browser()


if __name__ == "__main__":
    asyncio.run(test_production_system())