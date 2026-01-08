"""
Error Handler Middleware
Global exception handling with structured error responses
"""

import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle all exceptions and return structured error responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            logger.warning(f"HTTP Exception: {e.status_code} - {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": True,
                    "message": e.detail,
                    "status_code": e.status_code
                }
            )
        except Exception as e:
            logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "An internal server error occurred",
                    "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else None,
                    "status_code": 500
                }
            )
