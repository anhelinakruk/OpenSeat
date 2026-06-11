"""Parse a wagon's SVG seat map into a list of seats."""
import re

from .errors import InterCityError

# Every seat in the SVG has aria-label="Miejsce {number} ... {Niedostepne|...}, niewybrane".
_SEAT_RE = re.compile(r'aria-label="Miejsce (\d+)([^"]*)"')


def parse_seats(svg: str) -> list[dict]:
    """Return seats parsed from the SVG: {'number': str, 'free': bool}.

    A seat is free when its label does not contain "Niedostepne" (InterCity's word for "unavailable").
    Raises InterCityError if the SVG looks like a seat map but no seats match: that means the
    label format changed and we must not silently report every seat as free.
    """
    seats = []
    for match in _SEAT_RE.finditer(svg):
        number = match.group(1)
        label_rest = match.group(2)
        seats.append({"number": number, "free": "Niedostepne" not in label_rest})
    if "Miejsce" in svg and not seats:
        raise InterCityError("Could not parse seats from the wagon SVG (label format may have changed).")
    return seats
