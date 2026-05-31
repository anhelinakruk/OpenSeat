"""Configuration constants for the InterCity client (see docs/INTERCITY_API.md)."""

# Main API host (composition, seat maps, search, route).
API_GATEWAY = "https://api-gateway.intercity.pl"
# Station autocomplete host (different from api-gateway!).
WWW = "https://www.intercity.pl"

# "Device" number required in the `Pociagi` RPC body; without it the API replies "device inactive".
# Value observed in ebilet network traffic (see docs/INTERCITY_API.md).
DEVICE_NR = 956
# Client version string sent in POST bodies.
VERSION = "1.5.10_mobile"

# The `Origin` header is CRITICAL: without it Akamai drops the connection.
DEFAULT_HEADERS = {
    "Origin": "https://ebilet.intercity.pl",
    "Referer": "https://ebilet.intercity.pl/",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}
