"""
Parallel Processor
Process multiple forms in parallel with rate limiting
"""
from typing import List, Callable, Any, Optional
import asyncio
from collections import deque
import time

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
    
    async def acquire(self):
        """Acquire permission to make a call"""
        now = time.time()
        
        # Remove old calls outside time window
        while self.calls and self.calls[0] < now - self.time_window:
            self.calls.popleft()
        
        # Check if we're at limit
        if len(self.calls) >= self.max_calls:
            # Wait until oldest call expires
            wait_time = self.time_window - (now - self.calls[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Clean up again after waiting
                while self.calls and self.calls[0] < time.time() - self.time_window:
                    self.calls.popleft()
        
        # Record this call
        self.calls.append(time.time())

class ParallelProcessor:
    """Process items in parallel with concurrency and rate limiting"""
    
    def __init__(
        self,
        max_concurrent: int = 5,
        rate_limit: Optional[tuple] = None
    ):
        """
        Args:
            max_concurrent: Maximum concurrent operations
            rate_limit: Tuple of (max_calls, time_window_seconds) for rate limiting
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = None
        
        if rate_limit:
            self.rate_limiter = RateLimiter(rate_limit[0], rate_limit[1])
    
    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[Any]:
        """
        Process items in parallel
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            progress_callback: Optional callback(item, result) for progress updates
        
        Returns:
            List of results
        """
        tasks = []
        
        for item in items:
            task = self._process_item_with_limits(item, process_func, progress_callback)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "item": items[i],
                    "error": str(result),
                    "status": "error"
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_item_with_limits(
        self,
        item: Any,
        process_func: Callable,
        progress_callback: Optional[Callable]
    ):
        """Process item with concurrency and rate limiting"""
        async with self.semaphore:
            # Apply rate limiting if configured
            if self.rate_limiter:
                await self.rate_limiter.acquire()
            
            try:
                result = await process_func(item)
                
                if progress_callback:
                    await progress_callback(item, result)
                
                return result
            except Exception as e:
                if progress_callback:
                    await progress_callback(item, {"error": str(e)})
                raise

# Global instances for different use cases
parallel_processor = ParallelProcessor(max_concurrent=5)

# Rate-limited processors for API providers
gpt4_processor = ParallelProcessor(
    max_concurrent=3,
    rate_limit=(50, 60)  # 50 requests per minute
)

claude_processor = ParallelProcessor(
    max_concurrent=3,
    rate_limit=(50, 60)  # 50 requests per minute
)

