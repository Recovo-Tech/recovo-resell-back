# app/exceptions.py
"""Custom exceptions for standardized error handling across the application"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseShopifyException(Exception):
    """Base exception for all Shopify-related errors"""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)


class ShopifyAPIException(BaseShopifyException):
    """Exception for Shopify API-related errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        shopify_errors: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.status_code = status_code
        self.shopify_errors = shopify_errors or []
        super().__init__(message, details, original_error)


class ShopifyConnectionException(BaseShopifyException):
    """Exception for Shopify connection/timeout errors"""
    pass


class ShopifyAuthenticationException(BaseShopifyException):
    """Exception for Shopify authentication errors"""
    pass


class ShopifyRateLimitException(BaseShopifyException):
    """Exception for Shopify rate limit errors"""
    
    def __init__(
        self, 
        message: str = "Shopify API rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.retry_after = retry_after
        super().__init__(message, details, original_error)


class ProductNotFoundException(BaseShopifyException):
    """Exception for when a product is not found"""
    pass


class CategoryNotFoundException(BaseShopifyException):
    """Exception for when a category/collection is not found"""
    pass


class ValidationException(BaseShopifyException):
    """Exception for validation errors"""
    pass


class PaginationException(BaseShopifyException):
    """Exception for pagination-related errors"""
    pass


def standardize_shopify_error(error: Exception) -> HTTPException:
    """Convert custom exceptions to standardized HTTP responses"""
    
    if isinstance(error, ShopifyAuthenticationException):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "authentication_failed",
                "message": str(error),
                "details": error.details
            }
        )
    
    elif isinstance(error, ShopifyRateLimitException):
        headers = {}
        if error.retry_after:
            headers["Retry-After"] = str(error.retry_after)
        
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": str(error),
                "retry_after": error.retry_after,
                "details": error.details
            },
            headers=headers
        )
    
    elif isinstance(error, (ProductNotFoundException, CategoryNotFoundException)):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "resource_not_found",
                "message": str(error),
                "details": error.details
            }
        )
    
    elif isinstance(error, ValidationException):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "validation_failed",
                "message": str(error),
                "details": error.details
            }
        )
    
    elif isinstance(error, PaginationException):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "pagination_error",
                "message": str(error),
                "details": error.details
            }
        )
    
    elif isinstance(error, ShopifyConnectionException):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "shopify_connection_failed",
                "message": str(error),
                "details": error.details
            }
        )
    
    elif isinstance(error, ShopifyAPIException):
        # Map Shopify status codes to appropriate HTTP status codes
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        if error.status_code:
            if error.status_code == 400:
                http_status = status.HTTP_400_BAD_REQUEST
            elif error.status_code == 401:
                http_status = status.HTTP_401_UNAUTHORIZED
            elif error.status_code == 403:
                http_status = status.HTTP_403_FORBIDDEN
            elif error.status_code == 404:
                http_status = status.HTTP_404_NOT_FOUND
            elif error.status_code == 422:
                http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
            elif error.status_code == 429:
                http_status = status.HTTP_429_TOO_MANY_REQUESTS
        
        return HTTPException(
            status_code=http_status,
            detail={
                "error": "shopify_api_error",
                "message": str(error),
                "shopify_status_code": error.status_code,
                "shopify_errors": error.shopify_errors,
                "details": error.details
            }
        )
    
    elif isinstance(error, BaseShopifyException):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "shopify_error",
                "message": str(error),
                "details": error.details
            }
        )
    
    else:
        # Generic error handling for non-custom exceptions
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred"
            }
        )


def create_error_response(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
) -> HTTPException:
    """Create a standardized error response"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_type,
            "message": message,
            "details": details or {}
        }
    )
