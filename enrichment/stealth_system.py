#!/usr/bin/env python3
"""
Enhanced Anti-Detection System for Web Scraping
Implements advanced techniques to avoid detection and IP blocking
"""

import asyncio
import random
import time
import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging

logger = logging.getLogger(__name__)

class EnhancedStealthSystem:
    """
    Advanced anti-detection system with multiple layers of protection
    """
    
    def __init__(self):
        # Browser fingerprint rotation
        self.user_agents = [
            # Windows Chrome (most common)
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            
            # Windows Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            
            # Mac Chrome
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Mac Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            
            # Windows Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        ]
        
        # Viewport sizes (common resolutions)
        self.viewports = [
            {'width': 1920, 'height': 1080},  # Full HD
            {'width': 1366, 'height': 768},   # Laptop
            {'width': 1536, 'height': 864},   # Laptop HD+
            {'width': 1440, 'height': 900},   # MacBook
            {'width': 1600, 'height': 900},   # Widescreen
            {'width': 2560, 'height': 1440},  # 2K
        ]
        
        # Geographic locations for variety
        self.locations = [
            {'timezone_id': 'America/New_York', 'latitude': 40.7128, 'longitude': -74.0060, 'locale': 'en-US'},
            {'timezone_id': 'America/Los_Angeles', 'latitude': 34.0522, 'longitude': -118.2437, 'locale': 'en-US'},
            {'timezone_id': 'America/Chicago', 'latitude': 41.8781, 'longitude': -87.6298, 'locale': 'en-US'},
            {'timezone_id': 'America/Denver', 'latitude': 39.7392, 'longitude': -104.9903, 'locale': 'en-US'},
            {'timezone_id': 'America/Phoenix', 'latitude': 33.4484, 'longitude': -112.0740, 'locale': 'en-US'},
        ]
        
        # Session tracking
        self.session_data = {}
        self.last_request_time = {}
        
        # Free proxy services (use with caution - for educational purposes)
        self.proxy_sources = [
            # Note: These are examples - in production use paid proxy services
            # 'https://www.proxy-list.download/api/v1/get?type=https',
            # 'https://api.proxyscrape.com/v2/?request=get&protocol=http',
        ]
    
    def get_random_fingerprint(self) -> Dict[str, Any]:
        """
        Generate a random browser fingerprint
        """
        user_agent = random.choice(self.user_agents)
        viewport = random.choice(self.viewports)
        location = random.choice(self.locations)
        
        # Determine browser type from user agent
        browser_type = 'chrome'
        if 'Firefox' in user_agent:
            browser_type = 'firefox'
        elif 'Safari' in user_agent and 'Chrome' not in user_agent:
            browser_type = 'safari'
        elif 'Edg' in user_agent:
            browser_type = 'edge'
        
        return {
            'user_agent': user_agent,
            'viewport': viewport,
            'location': location,
            'browser_type': browser_type,
            'platform': 'Win32' if 'Windows' in user_agent else 'MacIntel',
            'language': location['locale'],
            'color_depth': random.choice([24, 32]),
            'device_memory': random.choice([4, 8, 16]),
            'hardware_concurrency': random.choice([4, 8, 12, 16]),
        }
    
    def get_realistic_headers(self, user_agent: str, browser_type: str) -> Dict[str, str]:
        """
        Generate realistic HTTP headers based on browser type
        """
        base_headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'en-US,en;q=0.8,es;q=0.6',
                'en-GB,en;q=0.9',
                'en-US,en;q=0.9,fr;q=0.8',
            ]),
            'Cache-Control': random.choice(['no-cache', 'max-age=0']),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if browser_type == 'chrome' or browser_type == 'edge':
            base_headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            })
        elif browser_type == 'firefox':
            base_headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'DNT': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
            })
        
        # Randomly include/exclude some headers
        if random.random() > 0.3:
            base_headers['DNT'] = '1'
        
        # Add referer occasionally (looks more natural)
        if random.random() > 0.7:
            base_headers['Referer'] = random.choice([
                'https://www.google.com/',
                'https://www.bing.com/',
                'https://duckduckgo.com/',
            ])
        
        return base_headers
    
    def get_advanced_stealth_script(self, fingerprint: Dict[str, Any]) -> str:
        """
        Generate advanced stealth JavaScript to inject
        """
        return f"""
        // Advanced WebDriver hiding
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{ name: 'Chrome PDF Plugin', description: 'Portable Document Format' }},
                {{ name: 'Chrome PDF Viewer', description: 'PDF Viewer' }},
                {{ name: 'Native Client', description: 'Native Client' }},
            ],
        }});
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {{
            get: () => ['{fingerprint['language']}', 'en'],
        }});
        
        // Override platform
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{fingerprint['platform']}',
        }});
        
        // Override hardware specs
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {fingerprint['device_memory']},
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {fingerprint['hardware_concurrency']},
        }});
        
        // Override screen properties
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {fingerprint['color_depth']},
        }});
        
        // Mock WebGL fingerprint
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{
                return 'Intel Inc.';
            }}
            if (parameter === 37446) {{
                return 'Intel(R) Iris(TM) Graphics 6100';
            }}
            return getParameter.apply(this, arguments);
        }};
        
        // Mock canvas fingerprint
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {{
            // Add slight randomization to canvas
            const context = this.getContext('2d');
            if (context) {{
                context.fillStyle = 'rgba({random.randint(0,255)},{random.randint(0,255)},{random.randint(0,255)},0.01)';
                context.fillRect(0, 0, 1, 1);
            }}
            return toDataURL.apply(this, arguments);
        }};
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => {{
            if (parameters.name === 'notifications') {{
                return Promise.resolve({{ state: Notification.permission }});
            }}
            return originalQuery(parameters);
        }};
        
        // Add slight timing variation
        const originalDate = Date.now;
        Date.now = function() {{
            return originalDate() + Math.floor(Math.random() * 10);
        }};
        
        // Mock battery API
        Object.defineProperty(navigator, 'getBattery', {{
            get: () => () => Promise.resolve({{
                charging: {str(random.choice([True, False])).lower()},
                chargingTime: {random.randint(3600, 7200)},
                dischargingTime: {random.randint(14400, 28800)},
                level: {round(random.uniform(0.2, 1.0), 2)},
            }}),
        }});
        """
    
    async def setup_browser_with_stealth(self, headless: bool = True) -> tuple[Browser, BrowserContext]:
        """
        Setup browser with advanced stealth configuration
        """
        fingerprint = self.get_random_fingerprint()
        
        playwright = await async_playwright().start()
        
        # Advanced browser arguments for stealth
        browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI,VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceLogging',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--use-mock-keychain',
            '--disable-plugins-discovery',
            '--disable-preconnect',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--mute-audio',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--disable-client-side-phishing-detection',
            '--disable-hang-monitor',
            '--disable-logging',
            '--disable-breakpad',
            '--disable-crash-reporter',
            '--no-crash-upload',
            '--disable-background-networking',
            '--disable-domain-reliability',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-features=VizDisplayCompositor',
            f'--user-agent={fingerprint["user_agent"]}',
        ]
        
        browser = await playwright.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # Create context with randomized fingerprint
        context = await browser.new_context(
            viewport=fingerprint['viewport'],
            user_agent=fingerprint['user_agent'],
            locale=fingerprint['location']['locale'],
            timezone_id=fingerprint['location']['timezone_id'],
            geolocation={
                'latitude': fingerprint['location']['latitude'],
                'longitude': fingerprint['location']['longitude']
            },
            permissions=['geolocation'],
            extra_http_headers=self.get_realistic_headers(
                fingerprint['user_agent'], 
                fingerprint['browser_type']
            ),
            # Enable JavaScript
            java_script_enabled=True,
            # Ignore HTTPS errors
            ignore_https_errors=True,
        )
        
        # Inject advanced stealth scripts
        await context.add_init_script(self.get_advanced_stealth_script(fingerprint))
        
        logger.info(f"Browser setup with fingerprint: {fingerprint['browser_type']} on {fingerprint['platform']}")
        
        return browser, context
    
    def calculate_smart_delay(self, last_request_time: Optional[datetime] = None) -> float:
        """
        Calculate intelligent delay that mimics human behavior
        """
        base_delay = random.uniform(0.5, 2.0)  # Ultra-aggressive: minimal delay  # Base delay 8-25 seconds
        
        # Add time-based variations
        current_hour = datetime.now().hour
        
        # Slower during business hours (more human activity)
        if 9 <= current_hour <= 17:
            base_delay *= random.uniform(1.0, 1.1)  # Ultra-aggressive: minimal penalty
        
        # Very slow during night hours (less activity)
        elif current_hour < 6 or current_hour > 22:
            base_delay *= random.uniform(1.0, 1.2)  # Ultra-aggressive: minimal penalty
        
        # Add occasional very long delays (human breaks)
        if random.random() < 0.01:  # Ultra-aggressive: rare breaks  # 10% chance
            base_delay *= random.uniform(1.2, 2)  # Ultra-aggressive: very short breaks
            logger.info(f"Taking extended break ({base_delay:.1f}s) - human behavior simulation")
        
        # Add variation based on last request time
        if last_request_time:
            time_since_last = (datetime.now() - last_request_time).total_seconds()
            if time_since_last < 30:  # Quick succession - add more delay
                base_delay *= random.uniform(1.2, 1.6)  # Optimized: reduced succession penalty
        
        return base_delay
    
    async def simulate_human_behavior(self, page: Page):
        """
        Simulate human-like behavior on the page
        """
        try:
            # Random mouse movements
            if random.random() < 0.7:  # 70% chance
                for _ in range(random.randint(1, 3)):
                    x = random.randint(100, 1800)
                    y = random.randint(100, 900)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.01, 0.1))  # Ultra-aggressive: fast movement
            
            # Random scrolling
            if random.random() < 0.5:  # 50% chance
                scroll_distance = random.randint(100, 800)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.01, 0.1))  # Ultra-aggressive: fast movement  # Ultra-aggressive: fast scroll
            
            # Random page interaction time
            await asyncio.sleep(random.uniform(0.5, 2))  # Ultra-aggressive: fast interaction
            
        except Exception as e:
            logger.debug(f"Human behavior simulation error: {e}")
    
    def track_session(self, session_id: str, action: str):
        """
        Track session activity for pattern analysis
        """
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                'start_time': datetime.now(),
                'actions': [],
                'request_count': 0,
            }
        
        self.session_data[session_id]['actions'].append({
            'action': action,
            'timestamp': datetime.now(),
        })
        self.session_data[session_id]['request_count'] += 1
        self.last_request_time[session_id] = datetime.now()


async def test_enhanced_stealth():
    """
    Test the enhanced stealth system
    """
    print("🕵️ Testing Enhanced Stealth System")
    print("=" * 40)
    
    stealth = EnhancedStealthSystem()
    
    try:
        browser, context = await stealth.setup_browser_with_stealth(headless=True)
        
        page = await context.new_page()
        
        # Test with a site that detects automation
        print("🔍 Testing stealth capabilities...")
        
        await page.goto('https://www.bing.com/search?q=test+search', wait_until='networkidle')
        
        # Simulate human behavior
        await stealth.simulate_human_behavior(page)
        
        # Check if we're detected
        title = await page.title()
        print(f"✅ Successfully loaded: {title}")
        
        # Take screenshot for verification
        await page.screenshot(path='stealth_test.png')
        print("📸 Screenshot saved: stealth_test.png")
        
        await browser.close()
        
        print("🎯 Enhanced stealth test completed successfully!")
        
    except Exception as e:
        print(f"❌ Stealth test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_enhanced_stealth())