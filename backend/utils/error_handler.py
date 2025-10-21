import asyncio
import traceback
import sys
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ErrorHandler:
    def __init__(self):
        self.error_counts = {}
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # seconds

    async def handle_api_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Global API error handler"""
        error_id = f"{type(exc).__name__}_{id(exc)}"

        # Log the error
        logger.error(f"API Error [{error_id}]: {str(exc)}")
        logger.error(f"Request: {request.method} {request.url}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Categorize error
        if isinstance(exc, HTTPException):
            status_code = exc.status_code
            error_type = "http_exception"
        elif isinstance(exc, ConnectionError):
            status_code = 503
            error_type = "connection_error"
        elif isinstance(exc, TimeoutError):
            status_code = 504
            error_type = "timeout_error"
        elif isinstance(exc, ValueError):
            status_code = 400
            error_type = "validation_error"
        else:
            status_code = 500
            error_type = "internal_error"

        # Track error frequency
        self._track_error(error_type)

        # Prepare error response
        error_response = {
            "error": {
                "type": error_type,
                "message": str(exc),
                "error_id": error_id,
                "timestamp": asyncio.get_event_loop().time()
            }
        }

        # Add debug info in development
        if hasattr(sys, '_getframe') and 'DEBUG' in str(sys._getframe()):
            error_response["error"]["traceback"] = traceback.format_exc()

        return JSONResponse(
            status_code=status_code,
            content=error_response
        )

    async def handle_websocket_error(self, websocket, exc: Exception):
        """Handle WebSocket-specific errors"""
        error_type = type(exc).__name__

        logger.error(f"WebSocket Error: {error_type} - {str(exc)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Try to send error message to client
        try:
            if websocket.client_state.name == 'CONNECTED':
                await websocket.send_json({
                    "error": {
                        "type": "websocket_error",
                        "message": str(exc),
                        "error_type": error_type
                    }
                })
        except Exception as send_error:
            logger.error(f"Failed to send error to websocket: {send_error}")

        # Track error
        self._track_error(f"websocket_{error_type}")

    async def retry_operation(self, operation, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]

                logger.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                logger.info(f"Retrying in {delay} seconds...")

                await asyncio.sleep(delay)

        # All retries failed
        logger.error(f"Operation failed after {self.max_retries} attempts: {str(last_exception)}")
        raise last_exception

    def _track_error(self, error_type: str):
        """Track error frequency for monitoring"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1

        # Log warning if error rate is high
        if self.error_counts[error_type] > 10:
            logger.warning(f"High error rate for {error_type}: {self.error_counts[error_type]} occurrences")

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "error_counts": self.error_counts.copy(),
            "total_errors": sum(self.error_counts.values()),
            "unique_error_types": len(self.error_counts)
        }

    def reset_error_stats(self):
        """Reset error statistics"""
        self.error_counts.clear()
        logger.info("Error statistics reset")

class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half_open'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if self.last_failure_time is None:
            return True

        elapsed = asyncio.get_event_loop().time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        if self.state == 'half_open':
            self.state = 'closed'
            self.failure_count = 0
            logger.info("Circuit breaker reset to CLOSED")

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time
        }

# Global instances
error_handler = ErrorHandler()
circuit_breaker = CircuitBreaker()
