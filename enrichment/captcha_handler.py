#!/usr/bin/env python3
"""
Advanced CAPTCHA Detection and Handling System
Detects various CAPTCHA types and implements appropriate responses
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)

class CaptchaHandler:
    """
    Comprehensive CAPTCHA detection and handling system
    """
    
    def __init__(self):
        # CAPTCHA detection patterns
        self.captcha_indicators = {
            'bing': [
                # Bing-specific CAPTCHA patterns
                'div[class*="captcha"]',
                'div[id*="captcha"]', 
                'iframe[src*="captcha"]',
                'div[class*="challenge"]',
                'div[class*="verification"]',
                '.b_captcha',
                '#captcha',
                'form[action*="captcha"]',
                
                # Cloudflare patterns
                'div[class*="cf-challenge"]',
                'div[id*="cf-challenge"]',
                '.cf-browser-verification',
                
                # reCAPTCHA patterns
                'div[class*="recaptcha"]',
                'iframe[src*="recaptcha"]',
                '.g-recaptcha',
                
                # hCaptcha patterns
                'div[class*="hcaptcha"]',
                'iframe[src*="hcaptcha"]',
                '.h-captcha',
                
                # Generic patterns
                'input[name*="captcha"]',
                'img[alt*="captcha" i]',
                'img[src*="captcha"]',
                'div[class*="robot-check"]',
                'div[class*="bot-check"]'
            ],
            'text_indicators': [
                'verify you are human',
                'complete the captcha',
                'prove you are not a robot',
                'security check',
                'verify your request',
                'unusual traffic',
                'automated requests',
                'bot detected',
                'please verify',
                'challenge required'
            ]
        }
        
        # CAPTCHA response strategies
        self.response_strategies = {
            'cloudflare_waiting': self._handle_cloudflare_challenge,
            'recaptcha': self._handle_recaptcha,
            'image_captcha': self._handle_image_captcha,
            'rate_limit': self._handle_rate_limit,
            'generic': self._handle_generic_captcha
        }
    
    async def detect_captcha(self, page: Page) -> Dict[str, Any]:
        """
        Comprehensive CAPTCHA detection across all major types
        
        Returns:
            {
                'detected': bool,
                'type': str,
                'confidence': float,
                'elements': list,
                'page_title': str,
                'page_url': str
            }
        """
        logger.info("🔍 Scanning for CAPTCHA/blocking indicators...")
        
        detection_result = {
            'detected': False,
            'type': 'none',
            'confidence': 0.0,
            'elements': [],
            'page_title': '',
            'page_url': '',
            'response_strategy': None
        }
        
        try:
            # Get page info
            detection_result['page_title'] = await page.title()
            detection_result['page_url'] = page.url
            
            # 1. Check for visual CAPTCHA elements
            visual_detection = await self._detect_visual_elements(page)
            
            # 2. Check page content for text indicators
            text_detection = await self._detect_text_indicators(page)
            
            # 3. Check for blocked/rate limited pages
            blocking_detection = await self._detect_blocking_patterns(page)
            
            # 4. Check for missing expected elements (like search results)
            missing_elements = await self._detect_missing_elements(page)
            
            # Combine all detection methods
            all_detections = [visual_detection, text_detection, blocking_detection, missing_elements]
            positive_detections = [d for d in all_detections if d['detected']]
            
            if positive_detections:
                # Choose highest confidence detection
                best_detection = max(positive_detections, key=lambda x: x['confidence'])
                detection_result.update(best_detection)
                
                # Determine response strategy
                detection_result['response_strategy'] = self._determine_response_strategy(detection_result)
                
                logger.warning(f"🚨 CAPTCHA/Block detected: {detection_result['type']} "
                             f"(confidence: {detection_result['confidence']:.1%})")
            else:
                logger.info("✅ No CAPTCHA/blocking detected")
                
        except Exception as e:
            logger.error(f"CAPTCHA detection error: {e}")
            # Assume blocked if detection fails
            detection_result.update({
                'detected': True,
                'type': 'detection_error',
                'confidence': 0.8,
                'response_strategy': 'generic'
            })
        
        return detection_result
    
    async def _detect_visual_elements(self, page: Page) -> Dict[str, Any]:
        """Detect CAPTCHA through visual elements"""
        try:
            found_elements = []
            
            for selector in self.captcha_indicators['bing']:
                elements = await page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        # Check if element is visible
                        is_visible = await element.is_visible()
                        if is_visible:
                            element_text = await element.text_content() or ""
                            found_elements.append({
                                'selector': selector,
                                'text': element_text[:100],  # First 100 chars
                                'visible': is_visible
                            })
            
            if found_elements:
                # Determine CAPTCHA type from elements
                captcha_type = self._classify_captcha_type(found_elements)
                confidence = min(0.9, 0.5 + len(found_elements) * 0.1)
                
                return {
                    'detected': True,
                    'type': captcha_type,
                    'confidence': confidence,
                    'elements': found_elements
                }
        
        except Exception as e:
            logger.debug(f"Visual element detection error: {e}")
        
        return {'detected': False, 'confidence': 0.0}
    
    async def _detect_text_indicators(self, page: Page) -> Dict[str, Any]:
        """Detect CAPTCHA through text content"""
        try:
            page_content = await page.content()
            page_text = page_content.lower()
            
            found_indicators = []
            for indicator in self.captcha_indicators['text_indicators']:
                if indicator in page_text:
                    found_indicators.append(indicator)
            
            if found_indicators:
                confidence = min(0.8, 0.3 + len(found_indicators) * 0.1)
                return {
                    'detected': True,
                    'type': 'text_based_challenge',
                    'confidence': confidence,
                    'indicators': found_indicators
                }
        
        except Exception as e:
            logger.debug(f"Text detection error: {e}")
        
        return {'detected': False, 'confidence': 0.0}
    
    async def _detect_blocking_patterns(self, page: Page) -> Dict[str, Any]:
        """Detect rate limiting or blocking patterns"""
        try:
            title = await page.title()
            url = page.url
            
            # Common blocking indicators
            blocking_patterns = [
                'blocked', 'rate limit', 'too many requests', 'access denied',
                'forbidden', 'service unavailable', 'temporarily unavailable',
                'unusual activity', 'suspicious activity'
            ]
            
            title_lower = title.lower()
            url_lower = url.lower()
            
            found_patterns = []
            for pattern in blocking_patterns:
                if pattern in title_lower or pattern in url_lower:
                    found_patterns.append(pattern)
            
            if found_patterns:
                return {
                    'detected': True,
                    'type': 'rate_limit_block',
                    'confidence': 0.7,
                    'patterns': found_patterns
                }
                
        except Exception as e:
            logger.debug(f"Blocking pattern detection error: {e}")
        
        return {'detected': False, 'confidence': 0.0}
    
    async def _detect_missing_elements(self, page: Page) -> Dict[str, Any]:
        """Detect blocking by missing expected elements"""
        try:
            # For Bing, we expect search result elements
            expected_selectors = [
                '.b_algo',      # Bing search results
                '.b_searchbox', # Bing search box
                '#b_results'    # Bing results container
            ]
            
            missing_elements = []
            for selector in expected_selectors:
                element = await page.query_selector(selector)
                if not element:
                    missing_elements.append(selector)
            
            # If critical elements are missing, likely blocked
            if '.b_algo' in missing_elements and '.b_searchbox' in missing_elements:
                return {
                    'detected': True,
                    'type': 'missing_search_elements',
                    'confidence': 0.6,
                    'missing': missing_elements
                }
                
        except Exception as e:
            logger.debug(f"Missing elements detection error: {e}")
        
        return {'detected': False, 'confidence': 0.0}
    
    def _classify_captcha_type(self, elements: List[Dict]) -> str:
        """Classify the type of CAPTCHA based on detected elements"""
        element_text = ' '.join([elem.get('text', '') for elem in elements]).lower()
        
        if 'cloudflare' in element_text or any('cf-' in elem['selector'] for elem in elements):
            return 'cloudflare_challenge'
        elif 'recaptcha' in element_text or any('recaptcha' in elem['selector'] for elem in elements):
            return 'recaptcha'
        elif 'hcaptcha' in element_text or any('hcaptcha' in elem['selector'] for elem in elements):
            return 'hcaptcha'
        elif any('img' in elem['selector'] for elem in elements):
            return 'image_captcha'
        else:
            return 'generic_captcha'
    
    def _determine_response_strategy(self, detection: Dict[str, Any]) -> str:
        """Determine the best response strategy for detected CAPTCHA"""
        captcha_type = detection.get('type', 'generic')
        
        strategy_mapping = {
            'cloudflare_challenge': 'cloudflare_waiting',
            'recaptcha': 'recaptcha',
            'hcaptcha': 'recaptcha',  # Similar handling
            'image_captcha': 'image_captcha',
            'rate_limit_block': 'rate_limit',
            'missing_search_elements': 'rate_limit',
            'text_based_challenge': 'generic',
            'detection_error': 'generic'
        }
        
        return strategy_mapping.get(captcha_type, 'generic')
    
    async def handle_captcha(self, page: Page, detection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle detected CAPTCHA based on type and strategy
        
        Returns:
            {
                'resolved': bool,
                'strategy_used': str,
                'time_taken': float,
                'fallback_needed': bool
            }
        """
        strategy = detection.get('response_strategy', 'generic')
        
        logger.info(f"🛠️ Handling CAPTCHA with strategy: {strategy}")
        
        start_time = time.time()
        
        try:
            if strategy in self.response_strategies:
                result = await self.response_strategies[strategy](page, detection)
            else:
                result = await self._handle_generic_captcha(page, detection)
            
            result['time_taken'] = time.time() - start_time
            result['strategy_used'] = strategy
            
            return result
            
        except Exception as e:
            logger.error(f"CAPTCHA handling error: {e}")
            return {
                'resolved': False,
                'strategy_used': strategy,
                'time_taken': time.time() - start_time,
                'fallback_needed': True,
                'error': str(e)
            }
    
    async def _handle_cloudflare_challenge(self, page: Page, detection: Dict) -> Dict[str, Any]:
        """Handle Cloudflare 'Checking your browser' challenge"""
        logger.info("⏳ Waiting for Cloudflare challenge to complete...")
        
        # Wait for Cloudflare to complete (usually 5-10 seconds)
        try:
            # Wait for the challenge page to disappear
            await page.wait_for_function(
                "!document.body.innerHTML.includes('Checking your browser')",
                timeout=30000
            )
            
            # Additional wait for page to fully load
            await asyncio.sleep(2)
            
            # Check if we now have search results
            search_results = await page.query_selector('.b_algo')
            if search_results:
                logger.info("✅ Cloudflare challenge completed successfully")
                return {'resolved': True, 'fallback_needed': False}
            else:
                logger.warning("⚠️ Cloudflare challenge completed but no search results")
                return {'resolved': False, 'fallback_needed': True}
                
        except Exception as e:
            logger.warning(f"Cloudflare challenge timeout: {e}")
            return {'resolved': False, 'fallback_needed': True}
    
    async def _handle_recaptcha(self, page: Page, detection: Dict) -> Dict[str, Any]:
        """Handle reCAPTCHA using 2captcha service"""
        logger.info("🔓 reCAPTCHA detected - attempting 2captcha solution")
        
        try:
            # Import 2captcha solver
            from .captcha_solver import TwoCaptchaSolver
            
            solver = TwoCaptchaSolver()
            
            if not solver.is_available():
                logger.warning("2captcha not available - falling back")
                return {'resolved': False, 'fallback_needed': True}
            
            # Try to find site key
            site_key = await self._extract_recaptcha_site_key(page)
            if not site_key:
                logger.warning("Could not extract reCAPTCHA site key")
                return {'resolved': False, 'fallback_needed': True}
            
            # Determine reCAPTCHA version
            is_v3 = await page.query_selector('[data-action]') is not None
            
            if is_v3:
                # Solve reCAPTCHA v3
                result = await solver.solve_recaptcha_v3(page, site_key)
            else:
                # Solve reCAPTCHA v2
                result = await solver.solve_recaptcha_v2(page, site_key)
            
            if result['success']:
                logger.info(f"✅ reCAPTCHA solved via 2captcha (${result['cost']:.3f})")
                
                # Wait a moment for injection to take effect
                await asyncio.sleep(2)
                
                # Check if we now have search results
                search_results = await page.query_selector('.b_algo')
                if search_results:
                    return {'resolved': True, 'fallback_needed': False, 'cost': result['cost']}
                else:
                    logger.warning("reCAPTCHA solved but no search results appeared")
                    return {'resolved': False, 'fallback_needed': True}
            else:
                logger.warning(f"reCAPTCHA solving failed: {result.get('error')}")
                return {'resolved': False, 'fallback_needed': True}
                
        except Exception as e:
            logger.error(f"reCAPTCHA handling error: {e}")
            return {'resolved': False, 'fallback_needed': True}
    
    async def _handle_image_captcha(self, page: Page, detection: Dict) -> Dict[str, Any]:
        """Handle image-based CAPTCHA using 2captcha OCR"""
        logger.info("🔓 Image CAPTCHA detected - attempting 2captcha OCR solution")
        
        try:
            # Import 2captcha solver
            from .captcha_solver import TwoCaptchaSolver
            
            solver = TwoCaptchaSolver()
            
            if not solver.is_available():
                logger.warning("2captcha not available - falling back")
                return {'resolved': False, 'fallback_needed': True}
            
            # Find CAPTCHA image
            image_element = await page.query_selector('img[alt*="captcha" i], img[src*="captcha"]')
            if not image_element:
                logger.warning("Could not find CAPTCHA image")
                return {'resolved': False, 'fallback_needed': True}
            
            # Solve using 2captcha
            result = await solver.solve_normal_captcha(page, image_element)
            
            if result['success']:
                logger.info(f"✅ Image CAPTCHA solved via 2captcha: '{result['solution']}' (${result['cost']:.3f})")
                
                # Submit form or continue
                submit_button = await page.query_selector('input[type="submit"], button[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    await asyncio.sleep(3)
                
                # Check if resolved
                search_results = await page.query_selector('.b_algo')
                if search_results:
                    return {'resolved': True, 'fallback_needed': False, 'cost': result['cost']}
                else:
                    return {'resolved': False, 'fallback_needed': True}
            else:
                logger.warning(f"Image CAPTCHA solving failed: {result.get('error')}")
                return {'resolved': False, 'fallback_needed': True}
                
        except Exception as e:
            logger.error(f"Image CAPTCHA handling error: {e}")
            return {'resolved': False, 'fallback_needed': True}
    
    async def _extract_recaptcha_site_key(self, page: Page) -> Optional[str]:
        """Extract reCAPTCHA site key from page"""
        try:
            # Common reCAPTCHA site key locations
            selectors = [
                '[data-sitekey]',
                '.g-recaptcha[data-sitekey]',
                'div[data-sitekey]'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    site_key = await element.get_attribute('data-sitekey')
                    if site_key:
                        return site_key
            
            # Try to find in page source
            content = await page.content()
            import re
            
            # Look for site key patterns
            patterns = [
                r'["\']sitekey["\']\s*:\s*["\']([^"\']+)["\']',
                r'data-sitekey=["\']([^"\']+)["\']',
                r'grecaptcha\.render\([^,]+,\s*{\s*["\']sitekey["\']\s*:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.debug(f"Site key extraction error: {e}")
            return None
    
    async def _handle_rate_limit(self, page: Page, detection: Dict) -> Dict[str, Any]:
        """Handle rate limiting by waiting and retrying"""
        logger.info("⏳ Rate limit detected - implementing backoff strategy...")
        
        # Progressive backoff
        wait_times = [30, 60, 120, 300]  # 30s, 1m, 2m, 5m
        
        for i, wait_time in enumerate(wait_times):
            logger.info(f"Waiting {wait_time} seconds (attempt {i+1}/{len(wait_times)})...")
            await asyncio.sleep(wait_time)
            
            # Refresh page and check if rate limit is lifted
            await page.reload()
            await asyncio.sleep(5)
            
            # Check for search results
            search_results = await page.query_selector('.b_algo')
            if search_results:
                logger.info("✅ Rate limit appears to be lifted")
                return {'resolved': True, 'fallback_needed': False}
        
        logger.warning("⚠️ Rate limit persists after multiple attempts")
        return {'resolved': False, 'fallback_needed': True}
    
    async def _handle_generic_captcha(self, page: Page, detection: Dict) -> Dict[str, Any]:
        """Generic CAPTCHA handling - basic waiting strategy"""
        logger.info("⏳ Generic CAPTCHA handling - waiting for manual resolution or timeout...")
        
        # Wait a bit to see if it resolves automatically
        await asyncio.sleep(10)
        
        # Check if resolved
        search_results = await page.query_selector('.b_algo')
        if search_results:
            return {'resolved': True, 'fallback_needed': False}
        else:
            return {'resolved': False, 'fallback_needed': True}