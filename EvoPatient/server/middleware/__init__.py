"""Middleware for rate limiting (simple in-memory for MVP)."""

import time
from collections import defaultdict

from fastapi import Request, HTTPException, status


class RateLimiter:
    """Simple sliding-window rate limiter per IP."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window

        # Prune old entries
        self._store[ip] = [t for t in self._store[ip] if t > cutoff]

        if len(self._store[ip]) >= self.max_requests:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

        self._store[ip].append(now)
