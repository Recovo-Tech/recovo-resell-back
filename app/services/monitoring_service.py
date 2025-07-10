# app/services/monitoring_service.py
"""Monitoring and observability service for Shopify operations"""

import time
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging

# Try to import structlog for better logging, fallback to standard logging
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    import logging
    HAS_STRUCTLOG = False


@dataclass
class MetricPoint:
    """Single metric measurement"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags
        }


@dataclass
class OperationMetrics:
    """Metrics for a specific operation"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    
    # Keep track of recent response times for percentile calculations
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Error tracking
    error_counts: Dict[str, int] = field(default_factory=dict)
    rate_limit_count: int = 0
    connection_error_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def average_duration(self) -> float:
        """Calculate average response time"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_duration / self.successful_requests
    
    def get_percentile_duration(self, percentile: int) -> float:
        """Get response time percentile (50, 90, 95, 99)"""
        if not self.recent_durations:
            return 0.0
        
        sorted_durations = sorted(self.recent_durations)
        index = int((percentile / 100) * len(sorted_durations))
        index = min(index, len(sorted_durations) - 1)
        return sorted_durations[index]
    
    def add_success(self, duration: float):
        """Record a successful operation"""
        self.total_requests += 1
        self.successful_requests += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)
        self.recent_durations.append(duration)
    
    def add_failure(self, error_type: str, duration: float = 0.0):
        """Record a failed operation"""
        self.total_requests += 1
        self.failed_requests += 1
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        if "rate_limit" in error_type.lower():
            self.rate_limit_count += 1
        elif "connection" in error_type.lower():
            self.connection_error_count += 1
        
        if duration > 0:
            self.total_duration += duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "average_duration": self.average_duration,
            "min_duration": self.min_duration if self.min_duration != float('inf') else 0,
            "max_duration": self.max_duration,
            "p50_duration": self.get_percentile_duration(50),
            "p90_duration": self.get_percentile_duration(90),
            "p95_duration": self.get_percentile_duration(95),
            "p99_duration": self.get_percentile_duration(99),
            "error_counts": dict(self.error_counts),
            "rate_limit_count": self.rate_limit_count,
            "connection_error_count": self.connection_error_count
        }


class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self.raw_metrics: List[MetricPoint] = []
        self._cleanup_interval = 3600  # Cleanup every hour
        self._last_cleanup = time.time()
    
    def record_operation(
        self,
        operation_name: str,
        duration: float,
        success: bool,
        error_type: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Record an operation result"""
        tags = tags or {}
        
        # Record in operation metrics
        if success:
            self.metrics[operation_name].add_success(duration)
        else:
            self.metrics[operation_name].add_failure(error_type or "unknown", duration)
        
        # Record raw metric point
        metric_point = MetricPoint(
            name=f"{operation_name}_duration",
            value=duration,
            timestamp=time.time(),
            tags={"success": str(success), **tags}
        )
        self.raw_metrics.append(metric_point)
        
        # Record success/failure as separate metrics
        status_metric = MetricPoint(
            name=f"{operation_name}_status",
            value=1.0 if success else 0.0,
            timestamp=time.time(),
            tags={"status": "success" if success else "failure", **tags}
        )
        self.raw_metrics.append(status_metric)
        
        # Cleanup old metrics periodically
        self._maybe_cleanup()
    
    def record_custom_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a custom metric"""
        metric_point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        self.raw_metrics.append(metric_point)
    
    def get_operation_metrics(self, operation_name: str) -> Dict[str, Any]:
        """Get metrics for a specific operation"""
        return self.metrics[operation_name].to_dict()
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return {
            "operations": {name: metrics.to_dict() for name, metrics in self.metrics.items()},
            "raw_metrics_count": len(self.raw_metrics),
            "collection_period_hours": self.retention_hours,
            "last_cleanup": self._last_cleanup
        }
    
    def get_metrics_for_export(self) -> List[Dict[str, Any]]:
        """Get metrics in format suitable for external monitoring systems"""
        return [metric.to_dict() for metric in self.raw_metrics]
    
    def _maybe_cleanup(self):
        """Clean up old metrics if needed"""
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_metrics(now)
            self._last_cleanup = now
    
    def _cleanup_old_metrics(self, current_time: float):
        """Remove metrics older than retention period"""
        cutoff_time = current_time - (self.retention_hours * 3600)
        self.raw_metrics = [
            metric for metric in self.raw_metrics 
            if metric.timestamp > cutoff_time
        ]


class ShopifyMonitoringService:
    """Main monitoring service for Shopify operations"""
    
    def __init__(self, tenant_id: str, metrics_collector: Optional[MetricsCollector] = None):
        self.tenant_id = tenant_id
        self.metrics_collector = metrics_collector or MetricsCollector()
        
        # Setup structured logging
        if HAS_STRUCTLOG:
            self.logger = structlog.get_logger().bind(
                tenant_id=tenant_id,
                service="shopify_monitoring"
            )
        else:
            self.logger = logging.getLogger(__name__)
    
    async def track_operation(
        self,
        operation_name: str,
        operation_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Track an operation with automatic metrics collection"""
        start_time = time.time()
        operation_tags = {
            "tenant_id": self.tenant_id,
            "operation": operation_name
        }
        
        try:
            self._log_operation_start(operation_name, args, kwargs)
            
            result = await operation_func(*args, **kwargs)
            
            duration = time.time() - start_time
            self.metrics_collector.record_operation(
                operation_name, duration, True, tags=operation_tags
            )
            
            self._log_operation_success(operation_name, duration, result)
            return result
            
        except Exception as error:
            duration = time.time() - start_time
            error_type = type(error).__name__
            
            self.metrics_collector.record_operation(
                operation_name, duration, False, error_type, operation_tags
            )
            
            self._log_operation_error(operation_name, duration, error)
            raise
    
    def track_cache_operation(self, operation: str, hit: bool, key: str):
        """Track cache hit/miss metrics"""
        self.metrics_collector.record_custom_metric(
            "cache_operation",
            1.0 if hit else 0.0,
            {
                "tenant_id": self.tenant_id,
                "operation": operation,
                "result": "hit" if hit else "miss",
                "cache_key_prefix": key.split(":")[0] if ":" in key else key
            }
        )
    
    def track_pagination_performance(self, page: int, limit: int, duration: float, product_count: int):
        """Track pagination-specific metrics"""
        self.metrics_collector.record_custom_metric(
            "pagination_performance",
            duration,
            {
                "tenant_id": self.tenant_id,
                "page": str(page),
                "limit": str(limit),
                "product_count": str(product_count),
                "page_type": "first" if page == 1 else "subsequent"
            }
        )
    
    def track_api_rate_limit(self, remaining_calls: Optional[int], reset_time: Optional[str]):
        """Track Shopify API rate limit status"""
        if remaining_calls is not None:
            self.metrics_collector.record_custom_metric(
                "api_rate_limit_remaining",
                float(remaining_calls),
                {"tenant_id": self.tenant_id}
            )
    
    def track_product_transformation(self, product_count: int, duration: float):
        """Track product data transformation performance"""
        self.metrics_collector.record_custom_metric(
            "product_transformation_duration",
            duration,
            {
                "tenant_id": self.tenant_id,
                "product_count": str(product_count)
            }
        )
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted data for monitoring dashboard"""
        all_metrics = self.metrics_collector.get_all_metrics()
        
        # Calculate health score based on success rates and performance
        health_score = self._calculate_health_score(all_metrics["operations"])
        
        return {
            "tenant_id": self.tenant_id,
            "health_score": health_score,
            "timestamp": datetime.utcnow().isoformat(),
            "operations": all_metrics["operations"],
            "summary": {
                "total_operations": sum(
                    op["total_requests"] for op in all_metrics["operations"].values()
                ),
                "overall_success_rate": self._calculate_overall_success_rate(
                    all_metrics["operations"]
                ),
                "average_response_time": self._calculate_average_response_time(
                    all_metrics["operations"]
                )
            }
        }
    
    def _calculate_health_score(self, operations: Dict[str, Any]) -> float:
        """Calculate overall health score (0-100)"""
        if not operations:
            return 100.0
        
        scores = []
        for op_metrics in operations.values():
            # Success rate weight: 70%
            success_score = op_metrics["success_rate"] * 0.7
            
            # Performance weight: 30% (based on average response time)
            avg_duration = op_metrics["average_duration"]
            # Consider <1s as good (100%), >5s as poor (0%)
            performance_score = max(0, (5.0 - avg_duration) / 5.0 * 100) * 0.3
            
            scores.append(success_score + performance_score)
        
        return sum(scores) / len(scores)
    
    def _calculate_overall_success_rate(self, operations: Dict[str, Any]) -> float:
        """Calculate overall success rate across all operations"""
        total_requests = sum(op["total_requests"] for op in operations.values())
        total_successful = sum(op["successful_requests"] for op in operations.values())
        
        if total_requests == 0:
            return 100.0
        
        return (total_successful / total_requests) * 100
    
    def _calculate_average_response_time(self, operations: Dict[str, Any]) -> float:
        """Calculate weighted average response time"""
        total_duration = sum(
            op["average_duration"] * op["successful_requests"] 
            for op in operations.values()
        )
        total_requests = sum(op["successful_requests"] for op in operations.values())
        
        if total_requests == 0:
            return 0.0
        
        return total_duration / total_requests
    
    def _log_operation_start(self, operation_name: str, args: tuple, kwargs: dict):
        """Log operation start"""
        if HAS_STRUCTLOG:
            self.logger.info("operation_started", operation=operation_name)
        else:
            self.logger.info(f"Started operation: {operation_name}")
    
    def _log_operation_success(self, operation_name: str, duration: float, result: Any):
        """Log successful operation"""
        result_summary = self._summarize_result(result)
        
        if HAS_STRUCTLOG:
            self.logger.info(
                "operation_completed",
                operation=operation_name,
                duration=duration,
                result_summary=result_summary
            )
        else:
            self.logger.info(
                f"Completed operation: {operation_name} in {duration:.3f}s - {result_summary}"
            )
    
    def _log_operation_error(self, operation_name: str, duration: float, error: Exception):
        """Log failed operation"""
        if HAS_STRUCTLOG:
            self.logger.error(
                "operation_failed",
                operation=operation_name,
                duration=duration,
                error=str(error),
                error_type=type(error).__name__
            )
        else:
            self.logger.error(
                f"Failed operation: {operation_name} after {duration:.3f}s - {error}"
            )
    
    def _summarize_result(self, result: Any) -> str:
        """Create a summary of operation result"""
        if isinstance(result, dict):
            if "products" in result:
                return f"Products: {len(result['products'])}"
            elif "collections" in result:
                return f"Collections: {len(result['collections'])}"
            else:
                return f"Dict with {len(result)} keys"
        elif isinstance(result, list):
            return f"List with {len(result)} items"
        else:
            return f"{type(result).__name__}"


# Global monitoring service instances (can be configured per tenant)
_monitoring_services: Dict[str, ShopifyMonitoringService] = {}


def get_monitoring_service(tenant_id: str) -> ShopifyMonitoringService:
    """Get or create monitoring service for tenant"""
    if tenant_id not in _monitoring_services:
        _monitoring_services[tenant_id] = ShopifyMonitoringService(tenant_id)
    return _monitoring_services[tenant_id]


def monitor_shopify_operation(operation_name: str):
    """Decorator for monitoring Shopify operations"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Try to extract tenant_id from first argument (service instance)
            tenant_id = "unknown"
            if args and hasattr(args[0], 'tenant') and hasattr(args[0].tenant, 'id'):
                tenant_id = str(args[0].tenant.id)
            
            monitoring_service = get_monitoring_service(tenant_id)
            return await monitoring_service.track_operation(
                operation_name, func, *args, **kwargs
            )
        return wrapper
    return decorator
