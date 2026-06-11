"""Per-IP rate limiting for the API.

Why: each /api/ request fans out into many calls to InterCity's API, which rate-limits and has
already blocked our IP once. Capping requests per client IP (the counter is kept in the cache)
keeps our upstream traffic down and returns 429 before a flood ever reaches InterCity.
"""
import time

from django.core.cache import cache
from django.http import JsonResponse

# Maximum number of requests per client IP per window, across the /api/ endpoints.
LIMIT = 30
WINDOW = 60  # seconds


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            ip = request.META.get("REMOTE_ADDR", "unknown")
            bucket = int(time.time() // WINDOW)
            key = f"ratelimit:{ip}:{bucket}"
            # add() initialises the counter to 1 only if the key is absent; otherwise incr().
            count = 1 if cache.add(key, 1, WINDOW) else cache.incr(key)
            if count > LIMIT:
                return JsonResponse(
                    {"error": "Too many requests. Please slow down."}, status=429)
        return self.get_response(request)
