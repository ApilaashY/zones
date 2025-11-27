"""
Threading integration for mixed CPU/IO workloads in business lookup processing.
"""

import asyncio
import concurrent.futures
import threading
from typing import List, Callable, Any, Dict
import time
import os
import json
from dataclasses import dataclass, asdict

@dataclass
class ProcessingTask:
    task_id: str
    task_type: str  # 'scrape', 'parse', 'file_io'
    input_data: Any
    result: Any = None
    success: bool = False
    error_message: str = ""
    execution_time: float = 0.0


class HybridTaskProcessor:
    """
    Combines asyncio for I/O operations with thread pools for CPU-intensive tasks.
    """
    
    def __init__(self, max_workers: int = 4, max_io_concurrent: int = 5):
        self.max_workers = max_workers
        self.max_io_concurrent = max_io_concurrent
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.io_semaphore = asyncio.Semaphore(max_io_concurrent)
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.thread_pool.shutdown(wait=True)
    
    async def run_cpu_task_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run CPU-intensive task in thread pool from async context.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    async def process_html_parsing_concurrent(self, html_contents: List[str], 
                                           business_names: List[str]) -> List[Dict]:
        """
        Parse multiple HTML contents concurrently using thread pool.
        """
        from concurrent_scraper import parse_business_details  # Your parsing function
        
        tasks = []
        for html, name in zip(html_contents, business_names):
            task = self.run_cpu_task_async(parse_business_details, html, name)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        parsed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                parsed_results.append({
                    'business_name': business_names[i],
                    'error': str(result),
                    'success': False
                })
            else:
                parsed_results.append(result)
        
        return parsed_results
    
    async def batch_file_operations(self, operations: List[Dict]) -> List[bool]:
        """
        Perform multiple file I/O operations concurrently.
        """
        async def single_file_op(operation):
            async with self.io_semaphore:
                return await self.run_cpu_task_async(
                    self._execute_file_operation, operation
                )
        
        tasks = [single_file_op(op) for op in operations]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _execute_file_operation(self, operation: Dict) -> bool:
        """
        Execute a single file operation in thread pool.
        """
        try:
            op_type = operation['type']
            
            if op_type == 'write':
                with open(operation['filename'], 'w', encoding='utf-8') as f:
                    f.write(operation['content'])
            
            elif op_type == 'read':
                with open(operation['filename'], 'r', encoding='utf-8') as f:
                    operation['result'] = f.read()
            
            elif op_type == 'json_write':
                with open(operation['filename'], 'w', encoding='utf-8') as f:
                    json.dump(operation['data'], f, indent=2)
            
            return True
            
        except Exception as e:
            operation['error'] = str(e)
            return False


# Integration with your existing business lookup
class OptimizedBusinessLookup:
    """
    Optimized business lookup that combines concurrent scraping with threaded processing.
    """
    
    def __init__(self, max_concurrent_scrapes: int = 5, max_worker_threads: int = 4):
        self.max_concurrent_scrapes = max_concurrent_scrapes
        self.max_worker_threads = max_worker_threads
    
    async def process_business_list_optimized(self, business_names: List[str]) -> Dict:
        """
        Process a list of businesses with maximum efficiency.
        """
        from concurrent_scraper import ConcurrentPlaywrightScraper
        
        start_time = time.time()
        
        # Phase 1: Concurrent web scraping
        print(f"Phase 1: Scraping {len(business_names)} businesses concurrently...")
        scrape_start = time.time()
        
        async with ConcurrentPlaywrightScraper(
            max_concurrent=self.max_concurrent_scrapes
        ) as scraper:
            scrape_results = await scraper.search_multiple_businesses(business_names)
        
        scrape_time = time.time() - scrape_start
        successful_scrapes = [r for r in scrape_results if r.success]
        
        print(f"Scraping completed in {scrape_time:.2f}s")
        print(f"Successful: {len(successful_scrapes)}/{len(business_names)}")
        
        # Phase 2: Concurrent HTML parsing
        print(f"Phase 2: Parsing {len(successful_scrapes)} HTML results...")
        parse_start = time.time()
        
        async with HybridTaskProcessor(max_workers=self.max_worker_threads) as processor:
            html_contents = [r.html_content for r in successful_scrapes]
            business_names_success = [r.business_name for r in successful_scrapes]
            
            parsed_results = await processor.process_html_parsing_concurrent(
                html_contents, business_names_success
            )
            
            # Phase 3: Concurrent file I/O operations
            print("Phase 3: Writing results to files...")
            file_operations = []
            
            # Prepare file operations
            for i, (scrape_result, parsed_result) in enumerate(
                zip(successful_scrapes, parsed_results)
            ):
                # HTML file operation
                if scrape_result.success and scrape_result.html_content:
                    file_operations.append({
                        'type': 'write',
                        'filename': f'output/business_{i}_raw.html',
                        'content': scrape_result.html_content
                    })
                
                # JSON results file operation
                if parsed_result.get('success'):
                    file_operations.append({
                        'type': 'json_write',
                        'filename': f'output/business_{i}_parsed.json',
                        'data': parsed_result
                    })
            
            # Execute file operations concurrently
            await processor.batch_file_operations(file_operations)
        
        parse_time = time.time() - parse_start
        total_time = time.time() - start_time
        
        # Compile results
        results = {
            'total_time': total_time,
            'scrape_time': scrape_time,
            'parse_time': parse_time,
            'total_businesses': len(business_names),
            'successful_scrapes': len(successful_scrapes),
            'successful_parses': sum(1 for r in parsed_results if r.get('success')),
            'scrape_results': scrape_results,
            'parsed_results': parsed_results,
            'performance_stats': {
                'avg_scrape_time': scrape_time / len(business_names),
                'avg_parse_time': parse_time / len(successful_scrapes) if successful_scrapes else 0,
                'businesses_per_second': len(business_names) / total_time,
                'speedup_factor': (len(business_names) * 10) / total_time  # Assuming 10s per sequential search
            }
        }
        
        return results


# Example parsing function (you'll need to implement based on your HTML structure)
def parse_business_details(html_content: str, business_name: str) -> Dict:
    """
    Parse business details from HTML content.
    This is CPU-intensive and benefits from threading.
    """
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract business information
        # This is a simplified example - adapt to your HTML structure
        details = {
            'business_name': business_name,
            'success': True,
            'incorporation_date': None,
            'status': None,
            'address': None,
            'business_type': None
        }
        
        # Add your parsing logic here
        # Look for specific elements, patterns, etc.
        
        return details
        
    except Exception as e:
        return {
            'business_name': business_name,
            'success': False,
            'error': str(e)
        }


# Synchronous wrapper
def run_optimized_business_lookup(business_names: List[str]) -> Dict:
    """
    Run the optimized business lookup synchronously.
    """
    lookup = OptimizedBusinessLookup()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        lookup.process_business_list_optimized(business_names)
    )


if __name__ == "__main__":
    # Test the optimized system
    test_businesses = [
        "MTD Products Limited",
        "Union Co-op", 
        "Concordia Club",
        "Grand River Hospital",
        "University of Waterloo",
        "Kitchener Housing Inc",
        "Region of Waterloo"
    ]
    
    print(f"Running optimized lookup for {len(test_businesses)} businesses...")
    
    results = run_optimized_business_lookup(test_businesses)
    
    print("\n=== PERFORMANCE RESULTS ===")
    print(f"Total time: {results['total_time']:.2f}s")
    print(f"Scraping time: {results['scrape_time']:.2f}s") 
    print(f"Processing time: {results['parse_time']:.2f}s")
    print(f"Success rate: {results['successful_scrapes']}/{results['total_businesses']} scrapes")
    print(f"Businesses per second: {results['performance_stats']['businesses_per_second']:.2f}")
    print(f"Estimated speedup: {results['performance_stats']['speedup_factor']:.1f}x")