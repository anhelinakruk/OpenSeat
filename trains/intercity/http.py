"""Thin HTTP client for the InterCity API: shared headers, timeout and request retries."""
import time

import requests

from . import config
from .errors import InterCityError

# Transient server errors worth retrying.
_RETRYABLE = {500, 502, 503, 504}
# Rate limiting / bot detection: do not retry aggressively, fail fast with a clear message.
_RATE_LIMIT = {418, 429}
_TIMEOUT = 30
_ATTEMPTS = 3
_BACKOFF = 1.5  # seconds, increasing per attempt


def _request(method: str, url: str, *, json_body: dict | None = None,
             extra_headers: dict | None = None) -> requests.Response:
    """Send a request with InterCity headers; retry transient errors, raise InterCityError otherwise."""
    headers = {**config.DEFAULT_HEADERS, **(extra_headers or {})}
    last_error: object = None
    for attempt in range(_ATTEMPTS):
        try:
            response = requests.request(method, url, headers=headers, json=json_body, timeout=_TIMEOUT)
        except requests.RequestException as exc:        # dropped connection / timeout (e.g. IP block)
            last_error = exc
            time.sleep(_BACKOFF * (attempt + 1))
            continue
        if response.status_code in _RATE_LIMIT:
            raise InterCityError(
                f"InterCity is rate limiting requests (HTTP {response.status_code}). Try again shortly."
            )
        if response.status_code in _RETRYABLE:
            last_error = InterCityError(f"HTTP {response.status_code} from {url}")
            time.sleep(_BACKOFF * (attempt + 1))
            continue
        response.raise_for_status()
        return response
    raise InterCityError(f"Could not reach InterCity ({url}): {last_error}")


def get(url: str, extra_headers: dict | None = None) -> requests.Response:
    """Send a GET request to the InterCity API."""
    return _request("GET", url, extra_headers=extra_headers)


def post(url: str, data: dict | None = None, extra_headers: dict | None = None) -> requests.Response:
    """Send a POST request (JSON body) to the InterCity API."""
    return _request("POST", url, json_body=data, extra_headers=extra_headers)
