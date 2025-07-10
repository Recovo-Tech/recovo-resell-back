# app/services/retry_service.py
"""Retry logic with exponential backoff for Shopify API calls"""

import asyncio
import random
import time
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass
from functools import wraps
import logging

from app.exceptions import (
    ShopifyAPIException,
    ShopifyConnectionException,
    ShopifyRateLimitException,
    ShopifyAuthenticationException
)

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomization to prevent thundering herd
    retry_on_rate_limit: bool = True
    retry_on_connection_error: bool = True
    retry_on_api_error: bool = False  # Only retry specific API errors
    retryable_api_status_codes: List[int] = None

    def __post_init__(self):
        if self.retryable_api_status_codes is None:
            # 500, 502, 503, 504 are generally retryable
            self.retryable_api_status_codes = [500, 502, 503, 504]


class RetryState:
    """Tracks retry state for a specific operation"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
        self.total_delay = 0.0
        self.start_time = time.time()
        self.last_error: Optional[Exception] = None

    def should_retry(self, error: Exception) -> bool:
        """Determine if we should retry based on the error and config"""
        self.attempt += 1
        self.last_error = error

        # Don't retry if max attempts reached
        if self.attempt >= self.config.max_attempts:
            return False

        # Check error type
        if isinstance(error, ShopifyAuthenticationException):
            # Never retry auth errors
            return False
        
        elif isinstance(error, ShopifyRateLimitException):
            return self.config.retry_on_rate_limit
        
        elif isinstance(error, ShopifyConnectionException):
            return self.config.retry_on_connection_error
        
        elif isinstance(error, ShopifyAPIException):
            if not self.config.retry_on_api_error:
                return False
            # Only retry specific status codes
            return (error.status_code in self.config.retryable_api_status_codes 
                   if error.status_code else False)
        
        else:
            # Unknown error type - don't retry by default
            return False

    def get_delay(self, error: Exception) -> float:
        """Calculate delay before next retry"""
        
        # Special handling for rate limit errors
        if isinstance(error, ShopifyRateLimitException) and error.retry_after:
            delay = float(error.retry_after)
            logger.info(f"Rate limited, waiting {delay}s as specified by Shopify")
            return delay

        # Calculate exponential backoff delay
        delay = self.config.base_delay * (self.config.exponential_base ** (self.attempt - 1))
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        # Ensure delay is positive
        delay = max(0.1, delay)
        
        self.total_delay += delay
        return delay


class ShopifyRetryService:
    """Service for handling retries of Shopify operations"""

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    async def execute_with_retry(
        self, 
        operation: Callable,
        *args,
        operation_name: str = "shopify_operation",
        **kwargs
    ) -> Any:
        """Execute an operation with retry logic"""
        
        retry_state = RetryState(self.config)
        
        while True:
            try:
                logger.debug(f"Attempting {operation_name} (attempt {retry_state.attempt + 1})")
                
                result = await operation(*args, **kwargs)
                
                # Log successful retry if this wasn't the first attempt
                if retry_state.attempt > 0:
                    logger.info(
                        f"{operation_name} succeeded after {retry_state.attempt + 1} attempts "
                        f"(total delay: {retry_state.total_delay:.2f}s)"
                    )
                
                return result
                
            except Exception as error:
                
                if not retry_state.should_retry(error):
                    logger.error(
                        f"{operation_name} failed after {retry_state.attempt} attempts: {error}"
                    )
                    raise error
                
                delay = retry_state.get_delay(error)
                
                logger.warning(
                    f"{operation_name} failed (attempt {retry_state.attempt}): {error}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)

    def with_retry(
        self, 
        operation_name: str = None,
        config: RetryConfig = None
    ):
        """Decorator for adding retry logic to functions"""
        
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                retry_config = config or self.config
                retry_service = ShopifyRetryService(retry_config)
                name = operation_name or f"{func.__module__}.{func.__name__}"
                
                return await retry_service.execute_with_retry(
                    func, *args, operation_name=name, **kwargs
                )
            
            return wrapper
        return decorator


class BatchRetryService:
    """Service for handling batch operations with retry logic"""

    def __init__(self, config: RetryConfig = None, max_concurrent: int = 5):
        self.config = config or RetryConfig()
        self.max_concurrent = max_concurrent
        self.retry_service = ShopifyRetryService(self.config)

    async def execute_batch_with_retry(
        self,
        operations: List[Dict[str, Any]],
        operation_name: str = "batch_operation"
    ) -> List[Dict[str, Any]]:
        """Execute a batch of operations with retry logic and concurrency control"""
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def execute_single_operation(op_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    operation = op_data['operation']
                    args = op_data.get('args', [])
                    kwargs = op_data.get('kwargs', {})
                    op_name = op_data.get('name', f"{operation_name}_item")
                    
                    result = await self.retry_service.execute_with_retry(
                        operation, *args, operation_name=op_name, **kwargs
                    )
                    
                    return {
                        'success': True,
                        'result': result,
                        'operation_data': op_data
                    }
                    
                except Exception as error:
                    logger.error(f"Batch operation {op_data.get('name', 'unknown')} failed: {error}")
                    return {
                        'success': False,
                        'error': str(error),
                        'error_type': type(error).__name__,
                        'operation_data': op_data
                    }

        # Execute all operations concurrently
        tasks = [execute_single_operation(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Log batch summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        logger.info(f"Batch {operation_name} completed: {successful} successful, {failed} failed")
        
        return results


# Commonly used retry configurations
SHOPIFY_DEFAULT_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    retry_on_rate_limit=True,
    retry_on_connection_error=True,
    retry_on_api_error=True
)

SHOPIFY_AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=60.0,
    exponential_base=1.5,
    retry_on_rate_limit=True,
    retry_on_connection_error=True,
    retry_on_api_error=True
)

SHOPIFY_CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=10.0,
    retry_on_rate_limit=True,
    retry_on_connection_error=False,
    retry_on_api_error=False
)

# Global retry service instance
default_retry_service = ShopifyRetryService(SHOPIFY_DEFAULT_RETRY)


# Convenience decorators
def shopify_retry(
    operation_name: str = None,
    config: RetryConfig = None
):
    """Decorator for adding default Shopify retry logic"""
    return default_retry_service.with_retry(operation_name, config)


def shopify_aggressive_retry(operation_name: str = None):
    """Decorator for aggressive retry logic (more attempts, faster)"""
    service = ShopifyRetryService(SHOPIFY_AGGRESSIVE_RETRY)
    return service.with_retry(operation_name)


def shopify_conservative_retry(operation_name: str = None):
    """Decorator for conservative retry logic (fewer attempts, rate limit only)"""
    service = ShopifyRetryService(SHOPIFY_CONSERVATIVE_RETRY)
    return service.with_retry(operation_name)
