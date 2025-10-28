#!/usr/bin/env python3
"""
Advanced Human Behavior Simulation System
Simulates realistic human interaction patterns to avoid detection
"""

import asyncio
import random
import math
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from playwright.async_api import Page, Mouse, Keyboard

logger = logging.getLogger(__name__)

class HumanBehaviorSimulator:
    """
    Sophisticated human behavior simulation for web automation
    """
    
    def __init__(self):
        # Human timing patterns
        self.timing_patterns = {
            'reading_speed': (2, 8),  # Words per second range
            'typing_speed': (0.1, 0.3),  # Seconds between keystrokes
            'mouse_speed': (50, 200),  # Pixels per second
            'scroll_speed': (100, 300),  # Pixels per scroll
            'pause_between_actions': (0.5, 2.0),  # Seconds
            'thinking_time': (1, 4),  # Seconds before major actions
        }
        
        # Mouse movement patterns
        self.mouse_patterns = {
            'natural_curve': True,
            'micro_movements': True,
            'hover_probability': 0.3,
            'click_offset_range': 5,  # Pixels from center
        }
        
        # Realistic viewport interactions
        self.interaction_patterns = {
            'scroll_probability': 0.7,
            'back_scroll_probability': 0.2,
            'idle_movements': 0.4,
            'tab_switch_probability': 0.1,
        }
    
    async def simulate_page_arrival(self, page: Page) -> None:
        """Simulate realistic behavior when arriving at a new page"""
        logger.debug("🧑 Simulating human page arrival behavior...")
        
        # Wait for page to load (human reaction time)
        await self._random_delay(0.5, 1.5)
        
        # Simulate reading page title/header
        await self._simulate_reading_behavior(page, focus_area='top')
        
        # Random small mouse movement (humans often move mouse when page loads)
        if random.random() < 0.6:
            await self._random_mouse_movement(page, small_movement=True)
    
    async def simulate_search_behavior(self, page: Page, search_term: str) -> None:
        """Simulate realistic search behavior"""
        logger.debug(f"🧑 Simulating human search for: {search_term}")
        
        # Find search box with human-like targeting
        search_box = await page.query_selector('input[type="search"], input[name="q"], #sb_form_q')
        
        if search_box:
            # Move to search box with natural mouse movement
            await self._move_to_element_naturally(page, search_box)
            
            # Click with slight offset (humans don't click exactly center)
            await self._human_click(page, search_box)
            
            # Small delay (humans pause before typing)
            await self._random_delay(0.3, 0.8)
            
            # Clear existing text with human-like selection
            await self._clear_search_box(page, search_box)
            
            # Type with realistic human timing
            await self._human_type(page, search_term)
            
            # Brief pause before hitting enter (humans review what they typed)
            await self._random_delay(0.5, 1.2)
            
            # Press Enter
            await page.keyboard.press('Enter')
            
        else:
            logger.warning("Search box not found for human behavior simulation")
    
    async def simulate_result_browsing(self, page: Page) -> None:
        """Simulate human browsing of search results"""
        logger.debug("🧑 Simulating human result browsing behavior...")
        
        # Wait for results to load (human processing time)
        await self._random_delay(1, 2.5)
        
        # Scroll down to see more results (humans often scroll)
        if random.random() < self.interaction_patterns['scroll_probability']:
            await self._natural_scroll(page, direction='down', amount=random.randint(200, 600))
            
            # Read/process results
            await self._simulate_reading_behavior(page, focus_area='results')
            
            # Sometimes scroll back up
            if random.random() < self.interaction_patterns['back_scroll_probability']:
                await self._natural_scroll(page, direction='up', amount=random.randint(100, 300))
        
        # Random mouse movements while "reading"
        for _ in range(random.randint(1, 3)):
            await self._random_mouse_movement(page)
            await self._random_delay(0.5, 1.5)
    
    async def simulate_idle_behavior(self, page: Page, duration: float = 2.0) -> None:
        """Simulate realistic idle behavior while waiting"""
        logger.debug(f"🧑 Simulating idle behavior for {duration:.1f}s...")
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # Random micro-actions
            action = random.choices(
                ['mouse_movement', 'small_scroll', 'pause'],
                weights=[0.4, 0.2, 0.4],
                k=1
            )[0]
            
            if action == 'mouse_movement':
                await self._random_mouse_movement(page, small_movement=True)
            elif action == 'small_scroll':
                await self._natural_scroll(page, direction=random.choice(['up', 'down']), amount=random.randint(50, 150))
            else:
                await self._random_delay(0.3, 0.8)
    
    async def _move_to_element_naturally(self, page: Page, element) -> None:
        """Move mouse to element with natural curved path"""
        try:
            # Get element position
            bbox = await element.bounding_box()
            if not bbox:
                return
            
            target_x = bbox['x'] + bbox['width'] / 2
            target_y = bbox['y'] + bbox['height'] / 2
            
            # Add small random offset (humans don't click exact center)
            offset_x = random.randint(-self.mouse_patterns['click_offset_range'], 
                                    self.mouse_patterns['click_offset_range'])
            offset_y = random.randint(-self.mouse_patterns['click_offset_range'], 
                                    self.mouse_patterns['click_offset_range'])
            
            target_x += offset_x
            target_y += offset_y
            
            # Move with natural curve
            await self._natural_mouse_movement(page, target_x, target_y)
            
        except Exception as e:
            logger.debug(f"Natural mouse movement error: {e}")
    
    async def _natural_mouse_movement(self, page: Page, target_x: float, target_y: float) -> None:
        """Simulate natural curved mouse movement"""
        try:
            # Get current mouse position (approximate)
            viewport = page.viewport_size
            start_x = random.randint(0, viewport['width'])
            start_y = random.randint(0, viewport['height'])
            
            # Calculate movement path with curve
            distance = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
            steps = max(10, int(distance / 20))  # More steps for longer distances
            
            # Create curved path (humans don't move in straight lines)
            control_point_x = (start_x + target_x) / 2 + random.randint(-50, 50)
            control_point_y = (start_y + target_y) / 2 + random.randint(-30, 30)
            
            for i in range(steps + 1):
                t = i / steps
                
                # Quadratic Bezier curve
                x = (1 - t)**2 * start_x + 2 * (1 - t) * t * control_point_x + t**2 * target_x
                y = (1 - t)**2 * start_y + 2 * (1 - t) * t * control_point_y + t**2 * target_y
                
                await page.mouse.move(x, y)
                
                # Variable speed (humans accelerate and decelerate)
                speed_factor = 1 - abs(0.5 - t)  # Faster in middle, slower at ends
                delay = (1 / self.timing_patterns['mouse_speed'][1]) * (1 / max(0.1, speed_factor))
                await asyncio.sleep(min(0.05, delay))
                
        except Exception as e:
            logger.debug(f"Natural mouse movement error: {e}")
            # Fallback to simple movement
            await page.mouse.move(target_x, target_y)
    
    async def _human_click(self, page: Page, element) -> None:
        """Simulate human-like clicking"""
        try:
            # Move to element first
            await self._move_to_element_naturally(page, element)
            
            # Brief pause before click (human hesitation)
            await self._random_delay(0.1, 0.3)
            
            # Click with slight hold time (humans don't click instantly)
            await page.mouse.down()
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await page.mouse.up()
            
        except Exception as e:
            logger.debug(f"Human click error: {e}")
            # Fallback to element click
            await element.click()
    
    async def _human_type(self, page: Page, text: str) -> None:
        """Simulate human typing with realistic timing and errors"""
        try:
            for i, char in enumerate(text):
                # Type character
                await page.keyboard.type(char)
                
                # Human typing delays with variation
                base_delay = random.uniform(*self.timing_patterns['typing_speed'])
                
                # Longer pause after spaces (natural word breaks)
                if char == ' ':
                    base_delay *= random.uniform(1.5, 2.5)
                
                # Occasional longer pauses (thinking)
                if random.random() < 0.05:  # 5% chance
                    base_delay *= random.uniform(2, 4)
                
                await asyncio.sleep(base_delay)
                
                # Occasional typos and corrections (small chance)
                if random.random() < 0.02 and i < len(text) - 1:  # 2% chance, not on last char
                    # Type wrong character
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    await page.keyboard.type(wrong_char)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    
                    # Backspace to correct
                    await page.keyboard.press('Backspace')
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
        except Exception as e:
            logger.debug(f"Human typing error: {e}")
            # Fallback to simple typing
            await page.keyboard.type(text)
    
    async def _clear_search_box(self, page: Page, search_box) -> None:
        """Clear search box in human-like way"""
        try:
            # Focus on search box
            await search_box.focus()
            
            # Select all text (Ctrl+A)
            await page.keyboard.press('Control+a')
            await asyncio.sleep(0.1)
            
            # Delete selected text
            await page.keyboard.press('Delete')
            
        except Exception as e:
            logger.debug(f"Search box clearing error: {e}")
    
    async def _natural_scroll(self, page: Page, direction: str = 'down', amount: int = 300) -> None:
        """Simulate natural scrolling behavior"""
        try:
            scroll_delta = amount if direction == 'down' else -amount
            
            # Multiple small scrolls instead of one big scroll (more human-like)
            small_scrolls = random.randint(3, 7)
            scroll_per_step = scroll_delta // small_scrolls
            
            for _ in range(small_scrolls):
                await page.mouse.wheel(0, scroll_per_step)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
        except Exception as e:
            logger.debug(f"Natural scroll error: {e}")
    
    async def _random_mouse_movement(self, page: Page, small_movement: bool = False) -> None:
        """Random mouse movement to simulate human presence"""
        try:
            viewport = page.viewport_size
            
            if small_movement:
                # Small movements within 100px radius
                current_x = viewport['width'] // 2
                current_y = viewport['height'] // 2
                new_x = current_x + random.randint(-100, 100)
                new_y = current_y + random.randint(-100, 100)
            else:
                # Larger movements
                new_x = random.randint(50, viewport['width'] - 50)
                new_y = random.randint(50, viewport['height'] - 50)
            
            await self._natural_mouse_movement(page, new_x, new_y)
            
        except Exception as e:
            logger.debug(f"Random mouse movement error: {e}")
    
    async def _simulate_reading_behavior(self, page: Page, focus_area: str = 'full') -> None:
        """Simulate human reading behavior with eye movement patterns"""
        try:
            if focus_area == 'top':
                # Focus on top of page (title, header)
                reading_time = random.uniform(1, 3)
            elif focus_area == 'results':
                # Focus on search results area
                reading_time = random.uniform(2, 5)
            else:
                # Full page reading
                reading_time = random.uniform(3, 8)
            
            # Simulate reading with micro-movements
            steps = int(reading_time * 2)  # 2 movements per second
            
            for _ in range(steps):
                # Small random movements (simulating eye tracking)
                await self._random_mouse_movement(page, small_movement=True)
                await asyncio.sleep(reading_time / steps)
                
        except Exception as e:
            logger.debug(f"Reading simulation error: {e}")
    
    async def _random_delay(self, min_seconds: float, max_seconds: float) -> None:
        """Random delay with realistic human timing distribution"""
        # Use beta distribution for more realistic timing (humans have bias toward shorter times)
        delay = random.betavariate(2, 5) * (max_seconds - min_seconds) + min_seconds
        await asyncio.sleep(delay)
    
    async def simulate_frustrated_user(self, page: Page) -> None:
        """Simulate behavior of user encountering CAPTCHA/blocking"""
        logger.debug("🧑 Simulating frustrated user behavior...")
        
        # Scroll around looking for content
        await self._natural_scroll(page, 'down', 200)
        await self._random_delay(1, 2)
        await self._natural_scroll(page, 'up', 150)
        await self._random_delay(0.5, 1)
        
        # Random mouse movements (looking around)
        for _ in range(random.randint(2, 4)):
            await self._random_mouse_movement(page)
            await self._random_delay(0.3, 0.8)
        
        # Simulate trying to refresh (Ctrl+R) occasionally
        if random.random() < 0.3:
            await page.keyboard.press('F5')
            await self._random_delay(2, 4)