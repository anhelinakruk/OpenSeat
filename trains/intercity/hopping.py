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


def _greedy_cover(legs_free: list[set], first_seat: Optional[Hashable] = None) -> Optional[list[tuple]]:
    """Greedily cover the whole trip; if ``first_seat`` is given it must be used from leg 0.

    Each step keeps the current seat as long as it stays free, then switches to the seat that
    reaches furthest. Returns (seat, leg_from, leg_to) tuples, or None if a leg cannot be covered.
    """
    n = len(legs_free)
    position = 0
    forced = first_seat
    plan: list[tuple] = []
    while position < n:
        if forced is not None:                            # forced choice for the first segment
            if forced not in legs_free[position]:
                return None
            seat, reach = forced, seat_reach(forced, legs_free, position)
            forced = None
        else:                                             # greedy: seat reaching furthest from here
            seat, reach = None, position
            for candidate in legs_free[position]:
                candidate_reach = seat_reach(candidate, legs_free, position)
                if candidate_reach > reach:
                    seat, reach = candidate, candidate_reach
            if seat is None:                              # nobody reaches further: a gap
                return None
        plan.append((seat, position, reach))
        position = reach
    return plan


def find_plan(legs_free: list[set]) -> Optional[list[tuple]]:
    """Return the single best (fewest-transfer) plan covering the whole trip, or None."""
    return _greedy_cover(legs_free)


def find_plans(legs_free: list[set], limit: int = 5) -> list[list[tuple]]:
    """Return up to ``limit`` distinct journey plans, fewest transfers first.

    Generates one candidate per seat available on the first leg (used as the starting seat),
    completes it greedily, then sorts by number of segments (= transfers + 1).
    """
    if not legs_free:
        return []
    plans: list[list[tuple]] = []
    seen: set[tuple] = set()
    for first_seat in legs_free[0]:
        plan = _greedy_cover(legs_free, first_seat)
        if plan is None:
            continue
        key = tuple(plan)
        if key not in seen:
            seen.add(key)
            plans.append(plan)
    plans.sort(key=len)                                   # fewer segments == fewer transfers
    return plans[:limit]
