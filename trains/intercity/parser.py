"""Parse a wagon's SVG seat map into a list of seats."""
import re

# Every seat in the SVG has aria-label="Miejsce {number} ... {Niedostepne|...}, niewybrane".
_SEAT_RE = re.compile(r'aria-label="Miejsce (\d+)([^"]*)"')


def parse_seats(svg: str) -> list[dict]:
    """Return seats parsed from the SVG: {'number': str, 'free': bool}.

    A seat is free when its label does not contain "Niedostepne" (InterCity's word for "unavailable").
    """
    seats = []
    for match in _SEAT_RE.finditer(svg):
        number = match.group(1)
        label_rest = match.group(2)
        seats.append({"number": number, "free": "Niedostepne" not in label_rest})
    return seats
