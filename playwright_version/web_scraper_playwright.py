"""
Web Scraper using Playwright for business registry searches.
This module provides a Playwright-based alternative to Selenium for web automation.
OPTIMIZED VERSION with concurrent capabilities and performance improvements.
"""

import asyncio
import os
import time
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import Optional, List, Dict
import concurrent.futures
from dataclasses import dataclass

# Configuration - Set these to control file output behavior
SAVE_DEBUG_FILES = True  # Set to False to disable saving HTML and debug files
OUTPUT_FOLDER = 'business_lookup_output'  # Folder name for organizing output files
MAX_CONCURRENT_SEARCHES = 3  # Number of concurrent searches (be respectful to server)
OPTIMIZED_TIMEOUTS = True  # Use shorter, smarter timeouts

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

@dataclass
class SearchResult:
    """Data class for search results with performance metrics."""
    business_name: str
    html_content: str
    success: bool
    error_message: str = ""
    search_time: float = 0.0
    response_size: int = 0


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
    
    async def initialize(self):
        """Initialize the scraper (alias for start method)."""
        await self.start()
    
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
        
        # Set optimized timeouts
        if OPTIMIZED_TIMEOUTS:
            self.page.set_default_timeout(15000)  # 15 seconds - faster failure detection
            self.page.set_default_navigation_timeout(30000)  # 30 seconds
        else:
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
    
    async def search_business_optimized(self, business_name: str) -> SearchResult:
        """
        Optimized business search with performance improvements.
        
        Args:
            business_name: Name of the business to search for
            
        Returns:
            SearchResult with performance metrics
        """
        start_time = time.time()
        
        try:
            print(f"Optimized search for: {business_name}")
            
            # Navigate with faster load strategy
            search_url = "https://www.appmybizaccount.gov.on.ca/onbis/master/viewInstance/view.pub?id=3abd3bce3cc0ad2a5f4d3e3394f70a887b5d3629f9b7ec72&_timestamp=576646948208925"
            
            await self.page.goto(search_url, wait_until='domcontentloaded')  # Faster than networkidle
            
            # Quick cookie handling with timeout
            try:
                await self.page.click("button:has-text('Accept all')", timeout=2000)
                await asyncio.sleep(0.3)  # Reduced wait time
            except:
                pass  # Cookie banner might not exist
            
            # Fill search box with error handling
            await self.page.wait_for_selector("#QueryString", timeout=10000)
            await self.page.fill("#QueryString", business_name)
            
            # Try different search button selectors (same as original)
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
                    button = self.page.locator(selector)
                    if await button.count() > 0:
                        await button.click(timeout=5000)
                        print(f"Search button clicked using {selector}")
                        search_clicked = True
                        break
                except Exception as e:
                    continue
            
            if not search_clicked:
                raise Exception("Could not find or click the search button")
            
            # Wait for page to load after clicking
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Smart wait for results instead of fixed delay
            await self._smart_wait_for_results()
            
            # Get page content
            html_content = await self.page.content()
            search_time = time.time() - start_time
            
            return SearchResult(
                business_name=business_name,
                html_content=html_content,
                success=True,
                search_time=search_time,
                response_size=len(html_content)
            )
            
        except Exception as e:
            search_time = time.time() - start_time
            print(f"Error in optimized search for {business_name}: {e}")
            return SearchResult(
                business_name=business_name,
                html_content="",
                success=False,
                error_message=str(e),
                search_time=search_time
            )
    
    async def _smart_wait_for_results(self, max_wait: float = 6.0):
        """
        Smart waiting that checks for actual content instead of fixed delays.
        Significantly faster than the original 10-second wait.
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check for results
                results = await self.page.query_selector_all("div.registerItemSearch-results-page-line-ItemBox")
                if results:
                    return  # Results found
                
                # Check for no results message
                no_results = await self.page.query_selector("text=/No results found|No matches found/i")
                if no_results:
                    return  # No results confirmed
                
                # If we've waited minimum time and no loading indicators, assume done
                if time.time() - start_time > 2.0:
                    loading_indicators = await self.page.query_selector("text=/Loading|Searching|Please wait/i")
                    if not loading_indicators:
                        return
                
                await asyncio.sleep(0.3)  # Check every 300ms
                
            except Exception:
                # If checking fails, use minimum wait time
                if time.time() - start_time > 2.0:
                    return
                await asyncio.sleep(0.3)
    
    async def search_multiple_concurrent(self, business_names: List[str]) -> List[SearchResult]:
        """
        Search multiple businesses using the same browser instance.
        More efficient than creating new instances for each search.
        
        Args:
            business_names: List of business names to search
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        for business_name in business_names:
            result = await self.search_business_optimized(business_name)
            results.append(result)
            
            # Brief pause between searches to be respectful
            await asyncio.sleep(0.5)
        
        return results


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


class ConcurrentBusinessProcessor:
    """
    Processes multiple businesses concurrently using browser context pools.
    Optimized for high-throughput business lookups with server-friendly throttling.
    """
    
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_SEARCHES):
        self.max_concurrent = max_concurrent
        self.browser = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def __aenter__(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
    
    async def _process_single_business(self, business_name: str) -> SearchResult:
        """Process a single business with context management."""
        async with self.semaphore:
            try:
                # Create isolated context for this search
                context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()
                
                # Use optimized search method
                scraper = PlaywrightScraper()
                scraper.browser = self.browser  # Reuse browser
                scraper.context = context
                scraper.page = page
                
                result = await scraper.search_business_optimized(business_name)
                
                await context.close()
                return result
                
            except Exception as e:
                print(f"Error processing {business_name}: {e}")
                return SearchResult(
                    business_name=business_name,
                    success=False,
                    error_message=str(e),
                    html_content=""
                )
    
    async def process_businesses(self, business_names: List[str], batch_size: int = 10) -> List[SearchResult]:
        """
        Process businesses in batches with concurrent execution.
        
        Args:
            business_names: List of business names to process
            batch_size: Number of businesses to process concurrently
            
        Returns:
            List of SearchResult objects
        """
        all_results = []
        
        # Process in batches to prevent overwhelming the server
        for i in range(0, len(business_names), batch_size):
            batch = business_names[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}: {len(batch)} businesses")
            
            # Process batch concurrently
            tasks = [self._process_single_business(name) for name in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    error_result = SearchResult(
                        business_name=batch[j],
                        success=False,
                        error_message=str(result),
                        html_content=""
                    )
                    all_results.append(error_result)
                else:
                    all_results.append(result)
            
            # Pause between batches to be server-friendly
            if i + batch_size < len(business_names):
                print(f"Completed batch {i//batch_size + 1}. Pausing before next batch...")
                await asyncio.sleep(2)  # 2-second pause between batches
        
        return all_results

async def search_businesses_concurrent(business_names: List[str]) -> List[SearchResult]:
    """
    Convenience function for concurrent business searches.
    
    Args:
        business_names: List of business names to search
        
    Returns:
        List of SearchResult objects with performance metrics
    """
    async with ConcurrentBusinessProcessor() as processor:
        return await processor.process_businesses(business_names)

# Performance testing and comparison functions
async def compare_performance(business_names: List[str], sample_size: int = 10):
    """
    Compare performance between optimized and original methods.
    
    Args:
        business_names: List of business names to test
        sample_size: Number of businesses to test (default: 10)
    """
    test_names = business_names[:sample_size]
    
    print(f"\n🔄 Performance Comparison Test")
    print(f"Testing {len(test_names)} businesses")
    print(f"Original vs Optimized vs Concurrent methods")
    print("=" * 60)
    
    # Test concurrent method
    print(f"\n⚡ Testing Concurrent Method...")
    concurrent_start = time.time()
    concurrent_results = await search_businesses_concurrent(test_names)
    concurrent_time = time.time() - concurrent_start
    concurrent_success = sum(1 for r in concurrent_results if r.success)
    
    # Test optimized sequential method
    print(f"\n🚀 Testing Optimized Sequential Method...")
    sequential_start = time.time()
    async with PlaywrightScraper() as scraper:
        await scraper.initialize()
        sequential_results = await scraper.search_multiple_concurrent(test_names)
    sequential_time = time.time() - sequential_start
    sequential_success = sum(1 for r in sequential_results if r.success)
    
    # Display results
    print(f"\n📊 Performance Results:")
    print(f"Concurrent Method:   {concurrent_time:.2f}s ({concurrent_success}/{len(test_names)} successful)")
    print(f"Sequential Method:   {sequential_time:.2f}s ({sequential_success}/{len(test_names)} successful)")
    
    if sequential_time > 0:
        improvement = ((sequential_time - concurrent_time) / sequential_time) * 100
        print(f"Performance Gain:    {improvement:.1f}% faster with concurrent")
    
    return {
        'concurrent': {'time': concurrent_time, 'success_count': concurrent_success},
        'sequential': {'time': sequential_time, 'success_count': sequential_success}
    }

if __name__ == "__main__":
    # Test the scraper with performance comparison
    test_businesses = [
        "MTD Products Limited",
        "Canadian Tire Corporation",
        "Shoppers Drug Mart Inc.",
        "Loblaws Inc.",
        "Hudson's Bay Company"
    ]
    
    print("🚀 Enhanced Playwright Scraper with Multithreading")
    print("=" * 60)
    
    # Run performance comparison
    async def main():
        await compare_performance(test_businesses, sample_size=3)
        
        # Test single optimized search
        print(f"\n🔍 Testing single optimized search...")
        async with PlaywrightScraper() as scraper:
            await scraper.initialize()
            result = await scraper.search_business_optimized("MTD Products Limited")
            print(f"Search completed: {result.success}")
            print(f"Time taken: {result.search_time:.2f}s")
            print(f"Content size: {result.response_size:,} characters")
    
    # Run the main function
    asyncio.run(main())