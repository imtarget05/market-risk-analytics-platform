import os
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if os.getenv("TESTING", "false").lower() == "true":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        window_start = now - self.period
        self._clients[client_ip] = [t for t in self._clients[client_ip] if t > window_start]

        if len(self._clients[client_ip]) >= self.calls:
            return Response(content="Rate limit exceeded", status_code=429)

        self._clients[client_ip].append(now)
        return await call_next(request)
