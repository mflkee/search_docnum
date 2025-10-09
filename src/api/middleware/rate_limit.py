import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to implement rate limiting for API endpoints.
    """

    def __init__(self, app, requests_limit: int = 10, window_size: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_size = window_size  # in seconds
        self.requests = defaultdict(list)  # Store request times by IP

    async def dispatch(self, request: Request, call_next):
        # Get client IP (considering potential proxies)
        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Clean old requests outside the window
        now = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window_size
        ]

        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_limit:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "message": f"Maximum {self.requests_limit} requests per {self.window_size} seconds"}
            )

        # Add current request
        self.requests[client_ip].append(now)

        # Continue with the request
        response = await call_next(request)
        return response
