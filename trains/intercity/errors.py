"""InterCity domain exceptions."""


class InterCityError(Exception):
    """Error talking to InterCity's (unofficial) API: rate limit, server error, or missing data."""
