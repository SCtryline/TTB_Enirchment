#!/usr/bin/env python3
"""
2captcha Integration using Official Python Package
Professional CAPTCHA solving for all major CAPTCHA types
"""

import os
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Try to import 2captcha package
try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False
    logger.warning("2captcha-python package not installed. Run: pip install 2captcha-python")

class TwoCaptchaSolver:
    """
    Professional CAPTCHA solving using 2captcha.com official Python package
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('TWOCAPTCHA_API_KEY')
        self.solver = None
        
        if self.api_key and TWOCAPTCHA_AVAILABLE:
            self.solver = TwoCaptcha(self.api_key)
        
        # Service costs and timing (2024 rates)
        self.service_costs = {
            'recaptcha_v2': 0.001,      # $0.001 per solve
            'recaptcha_v3': 0.002,      # $0.002 per solve  
            'hcaptcha': 0.001,          # $0.001 per solve
            'cloudflare_turnstile': 0.002,  # $0.002 per solve
            'normal_captcha': 0.001,    # $0.001 per solve
            'funcaptcha': 0.002,        # $0.002 per solve
            'geetest': 0.002,           # $0.002 per solve
        }
        
        # Usage tracking
        self.usage_stats = {
            'total_solved': 0,
            'total_cost': 0.0,
            'last_solve_time': 0,
            'session_solves': 0
        }
    
    def is_available(self) -> bool:
        """Check if 2captcha service is available"""
        return bool(self.solver and TWOCAPTCHA_AVAILABLE)
    
    async def solve_recaptcha_v2(self, page: Page, site_key: str) -> Dict[str, Any]:
        """
        Solve reCAPTCHA v2 using 2captcha service
        """
        if not self.is_available():
            return {
                'success': False, 
                'error': '2captcha not available',
                'setup_needed': True
            }
        
        page_url = page.url
        logger.info(f"🔓 Solving reCAPTCHA v2 via 2captcha (site_key: {site_key[:20]}...)")
        
        start_time = time.time()
        
        try:
            # Solve using 2captcha
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url
            )
            
            if result.get('code'):
                # Inject solution into page
                token = result['code']
                await self._inject_recaptcha_token(page, token)
                
                solve_time = time.time() - start_time
                cost = self.service_costs['recaptcha_v2']
                
                # Update stats
                self._update_usage_stats(cost, solve_time)
                
                logger.info(f"✅ reCAPTCHA v2 solved successfully (${cost:.3f}, {solve_time:.1f}s)")
                
                return {
                    'success': True,
                    'token': token,
                    'cost': cost,
                    'solve_time': solve_time,
                    'task_id': result.get('captchaId')
                }
            else:
                raise Exception("No solution received from 2captcha")
                
        except Exception as e:
            solve_time = time.time() - start_time
            logger.error(f"❌ reCAPTCHA v2 solving failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'solve_time': solve_time
            }
    
    async def solve_recaptcha_v3(self, page: Page, site_key: str, action: str = 'submit') -> Dict[str, Any]:
        """
        Solve reCAPTCHA v3 using 2captcha service
        """
        if not self.is_available():
            return {
                'success': False, 
                'error': '2captcha not available',
                'setup_needed': True
            }
        
        page_url = page.url
        logger.info(f"🔓 Solving reCAPTCHA v3 via 2captcha (action: {action})")
        
        start_time = time.time()
        
        try:
            # Solve using 2captcha
            result = self.solver.recaptcha(
                sitekey=site_key,
                url=page_url,
                version='v3',
                action=action,
                min_score=0.3  # Minimum score threshold
            )
            
            if result.get('code'):
                token = result['code']
                
                # Inject v3 solution
                await page.evaluate(f"""
                    window.grecaptchaV3Token = '{token}';
                    if (typeof grecaptcha !== 'undefined') {{
                        grecaptcha.ready(function() {{
                            window.grecaptchaExecuteOriginal = grecaptcha.execute;
                            grecaptcha.execute = function() {{
                                return Promise.resolve('{token}');
                            }};
                        }});
                    }}
                """)
                
                solve_time = time.time() - start_time
                cost = self.service_costs['recaptcha_v3']
                
                self._update_usage_stats(cost, solve_time)
                
                logger.info(f"✅ reCAPTCHA v3 solved successfully (${cost:.3f}, {solve_time:.1f}s)")
                
                return {
                    'success': True,
                    'token': token,
                    'cost': cost,
                    'solve_time': solve_time,
                    'task_id': result.get('captchaId')
                }
            else:
                raise Exception("No solution received from 2captcha")
                
        except Exception as e:
            solve_time = time.time() - start_time
            logger.error(f"❌ reCAPTCHA v3 solving failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'solve_time': solve_time
            }
    
    async def solve_hcaptcha(self, page: Page, site_key: str) -> Dict[str, Any]:
        """
        Solve hCaptcha using 2captcha service
        """
        if not self.is_available():
            return {
                'success': False, 
                'error': '2captcha not available',
                'setup_needed': True
            }
        
        page_url = page.url
        logger.info(f"🔓 Solving hCaptcha via 2captcha (site_key: {site_key[:20]}...)")
        
        start_time = time.time()
        
        try:
            # Solve using 2captcha
            result = self.solver.hcaptcha(
                sitekey=site_key,
                url=page_url
            )
            
            if result.get('code'):
                token = result['code']
                
                # Inject hCaptcha solution
                await page.evaluate(f"""
                    document.querySelector('[name="h-captcha-response"]').value = '{token}';
                    if (typeof hcaptcha !== 'undefined') {{
                        hcaptcha.getResponse = function() {{ return '{token}'; }};
                    }}
                """)
                
                solve_time = time.time() - start_time
                cost = self.service_costs['hcaptcha']
                
                self._update_usage_stats(cost, solve_time)
                
                logger.info(f"✅ hCaptcha solved successfully (${cost:.3f}, {solve_time:.1f}s)")
                
                return {
                    'success': True,
                    'token': token,
                    'cost': cost,
                    'solve_time': solve_time,
                    'task_id': result.get('captchaId')
                }
            else:
                raise Exception("No solution received from 2captcha")
                
        except Exception as e:
            solve_time = time.time() - start_time
            logger.error(f"❌ hCaptcha solving failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'solve_time': solve_time
            }
    
    async def solve_cloudflare_turnstile(self, page: Page, site_key: str) -> Dict[str, Any]:
        """
        Solve Cloudflare Turnstile using 2captcha service
        """
        if not self.is_available():
            return {
                'success': False, 
                'error': '2captcha not available',
                'setup_needed': True
            }
        
        page_url = page.url
        logger.info(f"🔓 Solving Cloudflare Turnstile via 2captcha")
        
        start_time = time.time()
        
        try:
            # Solve using 2captcha
            result = self.solver.turnstile(
                sitekey=site_key,
                url=page_url
            )
            
            if result.get('code'):
                token = result['code']
                
                # Inject Turnstile solution
                await page.evaluate(f"""
                    if (typeof turnstile !== 'undefined') {{
                        turnstile.getResponse = function() {{ return '{token}'; }};
                    }}
                    // Set in hidden input if present
                    const turnstileInput = document.querySelector('[name="cf-turnstile-response"]');
                    if (turnstileInput) {{
                        turnstileInput.value = '{token}';
                    }}
                """)
                
                solve_time = time.time() - start_time
                cost = self.service_costs['cloudflare_turnstile']
                
                self._update_usage_stats(cost, solve_time)
                
                logger.info(f"✅ Cloudflare Turnstile solved successfully (${cost:.3f}, {solve_time:.1f}s)")
                
                return {
                    'success': True,
                    'token': token,
                    'cost': cost,
                    'solve_time': solve_time,
                    'task_id': result.get('captchaId')
                }
            else:
                raise Exception("No solution received from 2captcha")
                
        except Exception as e:
            solve_time = time.time() - start_time
            logger.error(f"❌ Cloudflare Turnstile solving failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'solve_time': solve_time
            }
    
    async def solve_normal_captcha(self, page: Page, image_element) -> Dict[str, Any]:
        """
        Solve normal image CAPTCHA using 2captcha OCR
        """
        if not self.is_available():
            return {
                'success': False, 
                'error': '2captcha not available',
                'setup_needed': True
            }
        
        logger.info("🔓 Solving normal CAPTCHA via 2captcha OCR")
        
        start_time = time.time()
        
        try:
            # Screenshot the CAPTCHA image
            image_data = await image_element.screenshot()
            
            # Solve using 2captcha
            result = self.solver.normal(image_data)
            
            if result.get('code'):
                solution_text = result['code']
                
                # Find input field and enter solution
                input_field = await page.query_selector('input[name*="captcha"], input[id*="captcha"]')
                if input_field:
                    await input_field.fill(solution_text)
                
                solve_time = time.time() - start_time
                cost = self.service_costs['normal_captcha']
                
                self._update_usage_stats(cost, solve_time)
                
                logger.info(f"✅ Normal CAPTCHA solved: '{solution_text}' (${cost:.3f}, {solve_time:.1f}s)")
                
                return {
                    'success': True,
                    'solution': solution_text,
                    'cost': cost,
                    'solve_time': solve_time,
                    'task_id': result.get('captchaId')
                }
            else:
                raise Exception("No solution received from 2captcha")
                
        except Exception as e:
            solve_time = time.time() - start_time
            logger.error(f"❌ Normal CAPTCHA solving failed: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'solve_time': solve_time
            }
    
    async def _inject_recaptcha_token(self, page: Page, token: str) -> None:
        """Inject reCAPTCHA solution token into page"""
        try:
            await page.evaluate(f"""
                // Set response in textarea
                const responseElement = document.getElementById('g-recaptcha-response');
                if (responseElement) {{
                    responseElement.innerHTML = '{token}';
                    responseElement.value = '{token}';
                }}
                
                // Override grecaptcha.getResponse
                if (typeof grecaptcha !== 'undefined') {{
                    grecaptcha.getResponse = function() {{ return '{token}'; }};
                }}
                
                // Trigger callback if exists
                if (typeof window.recaptchaCallback === 'function') {{
                    window.recaptchaCallback('{token}');
                }}
            """)
            
        except Exception as e:
            logger.debug(f"reCAPTCHA token injection error: {e}")
    
    def _update_usage_stats(self, cost: float, solve_time: float) -> None:
        """Update usage statistics"""
        self.usage_stats['total_solved'] += 1
        self.usage_stats['total_cost'] += cost
        self.usage_stats['last_solve_time'] = solve_time
        self.usage_stats['session_solves'] += 1
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get current 2captcha account balance"""
        if not self.is_available():
            return {
                'success': False,
                'error': '2captcha not available'
            }
        
        try:
            balance = self.solver.balance()
            
            return {
                'success': True,
                'balance': balance,
                'currency': 'USD',
                'estimated_solves': {
                    'recaptcha_v2': int(balance / self.service_costs['recaptcha_v2']),
                    'recaptcha_v3': int(balance / self.service_costs['recaptcha_v3']),
                    'hcaptcha': int(balance / self.service_costs['hcaptcha']),
                    'normal_captcha': int(balance / self.service_costs['normal_captcha'])
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            'service_available': self.is_available(),
            'package_installed': TWOCAPTCHA_AVAILABLE,
            'api_key_configured': bool(self.api_key),
            'session_stats': self.usage_stats,
            'service_costs': self.service_costs,
            'setup_instructions': {
                'install_package': 'pip install 2captcha-python',
                'set_api_key': 'export TWOCAPTCHA_API_KEY="your_api_key_here"',
                'get_api_key': 'https://2captcha.com/enterpage'
            }
        }
    
    async def test_service(self) -> Dict[str, Any]:
        """Test 2captcha service availability"""
        if not TWOCAPTCHA_AVAILABLE:
            return {
                'available': False,
                'error': '2captcha-python package not installed',
                'install_command': 'pip install 2captcha-python'
            }
        
        if not self.api_key:
            return {
                'available': False,
                'error': 'TWOCAPTCHA_API_KEY not configured',
                'setup_instructions': [
                    '1. Sign up at https://2captcha.com',
                    '2. Get your API key from dashboard',
                    '3. Set environment variable: export TWOCAPTCHA_API_KEY="your_key"',
                    '4. Restart the application'
                ]
            }
        
        try:
            balance_info = await self.get_balance()
            
            if balance_info['success']:
                return {
                    'available': True,
                    'status': 'operational',
                    'balance': balance_info,
                    'estimated_daily_cost': {
                        'light_usage': '$0.05',  # ~50 solves
                        'moderate_usage': '$0.10',  # ~100 solves  
                        'heavy_usage': '$0.20'   # ~200 solves
                    }
                }
            else:
                return {
                    'available': False,
                    'error': f'API test failed: {balance_info["error"]}'
                }
                
        except Exception as e:
            return {
                'available': False,
                'error': f'Service test failed: {e}'
            }