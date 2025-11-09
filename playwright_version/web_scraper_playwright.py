"""
Web Scraper using Playwright for business registry searches.
This module provides a Playwright-based alternative to Selenium for web automation.
"""

import asyncio
import os
import time
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import Optional

# Configuration - Set these to control file output behavior
SAVE_DEBUG_FILES = True  # Set to False to disable saving HTML and debug files
OUTPUT_FOLDER = 'business_lookup_output'  # Folder name for organizing output files

def ensure_output_folder():
    """Create the output folder if it doesn't exist."""
    if SAVE_DEBUG_FILES and not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created output folder: {OUTPUT_FOLDER}")

def get_output_path(filename: str) -> str:
    """Get the full path for an output file."""
    if SAVE_DEBUG_FILES:
        ensure_output_folder()
        return os.path.join(OUTPUT_FOLDER, filename)
    return filename


class PlaywrightScraper:
    """Web scraper using Playwright for automated browser interactions."""
    
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """
        Initialize the Playwright scraper.
        
        Args:
            headless: Whether to run browser in headless mode
            slow_mo: Delay in milliseconds between operations (useful for debugging)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the browser and create a new page."""
        self.playwright = await async_playwright().start()
        
        # Launch Chromium browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
            ]
        )
        
        # Create browser context
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Create new page
        self.page = await self.context.new_page()
        
        # Set reasonable timeouts
        self.page.set_default_timeout(30000)  # 30 seconds
        self.page.set_default_navigation_timeout(60000)  # 60 seconds
        
        return self
    
    async def close(self):
        """Close the browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def get_page(self, url: str, wait_time: float = 3.0) -> str:
        """
        Navigate to a URL and return the page content.
        
        Args:
            url: URL to navigate to
            wait_time: Time to wait after page load
            
        Returns:
            Page HTML content as string
        """
        try:
            print(f"Navigating to: {url}")
            
            # Navigate to the URL
            await self.page.goto(url, wait_until='networkidle')
            
            # Wait for the page to stabilize
            await asyncio.sleep(wait_time)
            
            # Return page content
            content = await self.page.content()
            return content
            
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return ""
    
    async def fill_input(self, selector: str, value: str) -> bool:
        """
        Fill an input field with the given value.
        
        Args:
            selector: CSS selector for the input field
            value: Value to fill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.page.fill(selector, value)
            return True
        except Exception as e:
            print(f"Error filling input {selector}: {e}")
            return False
    
    async def click_element(self, selector: str) -> bool:
        """
        Click an element by selector.
        
        Args:
            selector: CSS selector for the element
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.page.click(selector)
            return True
        except Exception as e:
            print(f"Error clicking element {selector}: {e}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """
        Wait for an element to appear on the page.
        
        Args:
            selector: CSS selector to wait for
            timeout: Timeout in milliseconds
            
        Returns:
            True if element appears, False otherwise
        """
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            print(f"Timeout waiting for selector {selector}: {e}")
            return False
    
    async def get_text_content(self, selector: str) -> str:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector for the element
            
        Returns:
            Text content or empty string if not found
        """
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.text_content() or ""
            return ""
        except Exception as e:
            print(f"Error getting text content for {selector}: {e}")
            return ""
    
    async def screenshot(self, filename: str = "screenshot.png"):
        """
        Take a screenshot of the current page.
        
        Args:
            filename: Filename for the screenshot
        """
        try:
            await self.page.screenshot(path=filename)
            print(f"Screenshot saved as {filename}")
        except Exception as e:
            print(f"Error taking screenshot: {e}")


# Synchronous wrapper for compatibility with existing code
class WebScraperPlaywright:
    """
    Synchronous wrapper for PlaywrightScraper to maintain compatibility
    with the existing Selenium-based interface.
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize the synchronous wrapper.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self._scraper = None
        self._loop = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _get_or_create_loop(self):
        """Get or create an event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    
    async def _start_scraper(self):
        """Start the async scraper."""
        self._scraper = PlaywrightScraper(headless=self.headless)
        await self._scraper.start()
    
    def start(self):
        """Start the scraper synchronously."""
        self._loop = self._get_or_create_loop()
        self._loop.run_until_complete(self._start_scraper())
    
    def get_page(self, url: str, wait_time: float = 3.0) -> str:
        """
        Navigate to a URL and return the page content (synchronous).
        
        Args:
            url: URL to navigate to
            wait_time: Time to wait after page load
            
        Returns:
            Page HTML content as string
        """
        if not self._scraper:
            self.start()
        
        return self._loop.run_until_complete(
            self._scraper.get_page(url, wait_time)
        )
    
    def close(self):
        """Close the scraper synchronously."""
        if self._scraper and self._loop:
            self._loop.run_until_complete(self._scraper.close())
            self._scraper = None
    
    # Compatibility properties for Selenium-like interface
    @property
    def page_source(self) -> str:
        """Get current page source (compatibility property)."""
        if self._scraper and self._scraper.page:
            return self._loop.run_until_complete(self._scraper.page.content())
        return ""


# Async function for business lookup (main implementation)
async def search_ontario_business_async(business_name: str) -> str:
    """
    Search for a business in the Ontario Business Registry using Playwright.
    
    Args:
        business_name: Name of the business to search for
        
    Returns:
        HTML content of the search results page
    """
    async with PlaywrightScraper(headless=False) as scraper:  # Set to True in production
        try:
            # Navigate to the search page
            print(f"Searching for: {business_name}")
            search_url = "https://www.appmybizaccount.gov.on.ca/onbis/master/viewInstance/view.pub?id=3abd3bce3cc0ad2a5f4d3e3394f70a887b5d3629f9b7ec72&_timestamp=576646948208925"
            print(f"Accessing: {search_url}")
            
            await scraper.page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Try to accept cookies if banner appears
            try:
                cookie_button = scraper.page.locator("button:has-text('Accept all')")
                if await cookie_button.count() > 0:
                    await cookie_button.click()
                    print("Accepted cookies")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"No cookie banner found or could not accept cookies: {e}")
            
            # Wait for search box and fill it
            search_box_selector = "#QueryString"
            try:
                await scraper.page.wait_for_selector(search_box_selector, timeout=10000)
                await scraper.page.fill(search_box_selector, "")  # Clear first
                await scraper.page.fill(search_box_selector, business_name)
                print("Search term entered")
            except Exception as e:
                print(f"Error filling search box: {e}")
                return ""
            
            # Try different search button selectors
            search_button_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Search')",
                "button:has-text('SEARCH')",
                "input[value='Search']",
                "input[value='SEARCH']",
                "#nodeW20"  # Original ID as fallback
            ]
            
            search_clicked = False
            for selector in search_button_selectors:
                try:
                    button = scraper.page.locator(selector)
                    if await button.count() > 0:
                        await button.click()
                        print(f"Search button clicked using {selector}")
                        search_clicked = True
                        break
                except Exception as e:
                    print(f"Tried selector {selector} but failed: {e}")
            
            if not search_clicked:
                print("Could not find or click the search button")
                return ""
            
            # Wait for results to load
            print("Waiting for results...")
            await asyncio.sleep(10)  # Give time for results to load
            
            # Save page source for debugging
            page_content = await scraper.page.content()
            if SAVE_DEBUG_FILES:
                debug_file = get_output_path('search_results_page.html')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_content)
                print(f"Saved search results page for debugging: {debug_file}")
            else:
                print("Debug file saving disabled - skipping search_results_page.html")
            
            # Check for results
            result_selectors = [
                "div.registerItemSearch-results-page-line-ItemBox",
                "div.search-results",
                "div.result-item",
                "div.search-result"
            ]
            
            results_found = False
            for selector in result_selectors:
                results = scraper.page.locator(selector)
                count = await results.count()
                if count > 0:
                    print(f"Found {count} results with selector: {selector}")
                    results_found = True
                    break
            
            if not results_found:
                print("Warning: No results found with any selector")
                # Check for "no results" message
                no_results = scraper.page.locator("text=/No results found|No matches found/i")
                if await no_results.count() > 0:
                    print("No results found for the search term")
            
            return page_content
            
        except Exception as e:
            print(f"Unexpected error during search: {e}")
            import traceback
            traceback.print_exc()
            return ""


# Synchronous wrapper for compatibility
def search_ontario_business_playwright(business_name: str) -> str:
    """
    Synchronous wrapper for the async search function.
    
    Args:
        business_name: Name of the business to search for
        
    Returns:
        HTML content of the search results page
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(search_ontario_business_async(business_name))


if __name__ == "__main__":
    # Test the scraper
    test_business = "MTD Products Limited"
    result = search_ontario_business_playwright(test_business)
    print(f"Search completed. Result length: {len(result)} characters")