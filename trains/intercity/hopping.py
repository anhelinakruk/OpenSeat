"""Algorithm that assembles a journey from seats free on individual legs.

Representation: ``legs_free`` is a list of sets, one per route "leg" (the segment between two
consecutive stops). Each set holds identifiers of seats free on that leg (e.g. the number
"61", or a (wagon, "61") pair across the whole train). The algorithm is generic: it does not
care what a seat identifier actually is.
"""
from typing import Hashable, Optional


def fully_free_seats(legs_free: list[set]) -> set:
    """Return seats free on EVERY leg (the intersection): a trip with no seat change."""
    if not legs_free:
        return set()
    result = legs_free[0]
    for leg in legs_free[1:]:
        result = result & leg
    return result


def seat_reach(seat: Hashable, legs_free: list[set], start: int) -> int:
    """Return the first leg (from ``start``) where ``seat`` is no longer free, or the trip length."""
    i = start
    while i < len(legs_free) and seat in legs_free[i]:
        i += 1
    return i


def find_plan(legs_free: list[set]) -> Optional[list[tuple]]:
    """Return the smallest (greedy) set of seats covering the whole trip.

    The result is a list of (seat, leg_from, leg_to) tuples; the number of transfers is
    ``len(plan) - 1``. Returns None when the trip cannot be covered (a leg has no free seat).
    """
    n = len(legs_free)
    position = 0
    plan: list[tuple] = []
    while position < n:
        best_seat: Optional[Hashable] = None
        best_reach = position
        for seat in legs_free[position]:                  # candidates: seats free here and now
            reach = seat_reach(seat, legs_free, position)
            if reach > best_reach:                        # keep the one that reaches furthest
                best_seat = seat
                best_reach = reach
        if best_seat is None:                             # nobody reaches further: a gap
            return None
        plan.append((best_seat, position, best_reach))
        position = best_reach
    return plan
