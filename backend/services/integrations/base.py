"""
CONFIT Backend - Base Integration Class
=======================================
Abstract base class for all external service integrations.
Provides retry logic, structured logging, and HTTP client management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TypeVar, Generic
from functools import wraps

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class IntegrationError(Exception):
    """Base exception for integration failures."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.response_data = response_data or {}
        self.original_error = original_error
        self.timestamp = datetime.now(timezone.utc)


class BaseIntegration(ABC, Generic[T]):
    """
    Abstract base class for external service integrations.
    
    Features:
    - Configurable timeout and retry logic
    - Structured logging of all API calls
    - Reusable HTTP client via property
    - Consistent error handling
    
    Every new provider must extend this class.
    """
    
    # Class-level HTTP client pool (shared across instances)
    _http_client: Optional[httpx.AsyncClient] = None
    
    def __init__(
        self,
        provider: str,
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        base_url: Optional[str] = None,
    ):
        """
        Initialize integration.
        
        Args:
            provider: Name of the provider (e.g., "twilio", "firebase")
            timeout_seconds: HTTP request timeout
            max_retries: Maximum retry attempts
            base_url: Base URL for API calls
        """
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_url = base_url
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """
        Get or create shared HTTP client.
        Reuses connection pool across requests.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
            )
        return self._http_client
    
    async def close(self) -> None:
        """Close HTTP client connection pool."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
    
    def _log_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> None:
        """Log outgoing request with structured data."""
        logger.info(
            f"[{self.provider}] API call started",
            extra={
                "provider": self.provider,
                "method": method,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    def _log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        """Log response with structured data."""
        level = logging.ERROR if error else logging.INFO
        logger.log(
            level,
            f"[{self.provider}] API call completed",
            extra={
                "provider": self.provider,
                "method": method,
                "url": url,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG),
    )
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Execute HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL or endpoint path
            **kwargs: Additional httpx request parameters
            
        Returns:
            httpx.Response object
            
        Raises:
            IntegrationError: On non-retryable failures
        """
        # Prepend base_url if url is relative
        if self.base_url and not url.startswith("http"):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        self._log_request(method, url, **kwargs)
        start_time = datetime.now(timezone.utc)
        
        try:
            response = await self.http_client.request(method, url, **kwargs)
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            self._log_response(
                method,
                url,
                response.status_code,
                duration_ms,
            )
            
            return response
            
        except httpx.TimeoutException as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._log_response(method, url, 0, duration_ms, error="timeout")
            raise IntegrationError(
                f"Request timeout after {self.timeout_seconds}s",
                provider=self.provider,
                original_error=e,
            )
            
        except httpx.NetworkError as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._log_response(method, url, 0, duration_ms, error=str(e))
            raise IntegrationError(
                f"Network error: {e}",
                provider=self.provider,
                original_error=e,
            )
    
    async def _request_json(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute HTTP request and parse JSON response.
        
        Raises:
            IntegrationError: On HTTP errors or invalid JSON
        """
        response = await self._request(method, url, **kwargs)
        
        if not response.is_success:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"raw": response.text}
            
            raise IntegrationError(
                f"API error: {response.status_code}",
                provider=self.provider,
                status_code=response.status_code,
                response_data=error_data,
            )
        
        try:
            return response.json()
        except Exception as e:
            raise IntegrationError(
                "Invalid JSON response",
                provider=self.provider,
                original_error=e,
            )
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the integration is healthy and credentials are valid.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
