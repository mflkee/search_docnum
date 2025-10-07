import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logging_config import app_logger


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle errors and log them appropriately.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the error with traceback
            app_logger.error(f"Unhandled exception for {request.method} {request.url.path}: {e!s}")
            app_logger.error(f"Traceback: {traceback.format_exc()}")

            # Return a user-friendly error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred. Please try again later."
                }
            )
