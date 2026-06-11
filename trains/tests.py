"""Tests for the seat-hopping algorithm and the InterCity parser/client (no network, no database)."""
from unittest import mock

from django.test import SimpleTestCase

from trains.intercity import client, parser
from trains.intercity.errors import InterCityError
from trains.intercity.hopping import find_plan, find_plans, fully_free_seats, seat_reach


class FullyFreeSeatsTests(SimpleTestCase):
    def test_common_seat(self):
        legs = [{"61", "16"}, {"61"}, {"61", "5"}]
        self.assertEqual(fully_free_seats(legs), {"61"})

    def test_no_common_seat(self):
        legs = [{"1", "2"}, {"2", "3"}, {"4"}]
        self.assertEqual(fully_free_seats(legs), set())

    def test_empty(self):
        self.assertEqual(fully_free_seats([]), set())


class SeatReachTests(SimpleTestCase):
    def test_stops_midway(self):
        legs = [{"61"}, {"61"}, {"61"}, set()]      # free on 0,1,2; taken on 3
        self.assertEqual(seat_reach("61", legs, 0), 3)

    def test_reaches_end(self):
        legs = [{"61"}, {"61"}]
        self.assertEqual(seat_reach("61", legs, 0), 2)

    def test_taken_at_start(self):
        legs = [set(), {"61"}]
        self.assertEqual(seat_reach("61", legs, 0), 0)


class FindPlanTests(SimpleTestCase):
    def test_no_transfer_when_seat_covers_all(self):
        legs = [{"7"}, {"7"}, {"7"}]
        plan = find_plan(legs)
        self.assertEqual(plan, [("7", 0, 3)])
        self.assertEqual(len(plan) - 1, 0)              # 0 transfers

    def test_single_transfer(self):
        # 61: free on legs 0-4; 16: free on legs 0,1 and 5 -> transfer on leg 5
        legs = [{"61", "16"}, {"61", "16"}, {"61"}, {"61"}, {"61"}, {"16"}]
        plan = find_plan(legs)
        self.assertEqual(plan, [("61", 0, 5), ("16", 5, 6)])
        self.assertEqual(len(plan) - 1, 1)              # 1 transfer

    def test_impossible_when_gap(self):
        legs = [{"1"}, set(), {"1"}]                    # leg 1 has no free seat
        self.assertIsNone(find_plan(legs))

    def test_prefers_fewest_transfers(self):
        # seat "A" covers the whole trip -> chosen over other candidates
        legs = [{"A", "B"}, {"A", "C"}, {"A"}]
        plan = find_plan(legs)
        self.assertEqual(plan, [("A", 0, 3)])


class FindPlansTests(SimpleTestCase):
    def test_multiple_full_trip_seats(self):
        # three seats free the whole way -> three zero-transfer options
        legs = [{"1", "2", "3"}, {"1", "2", "3"}]
        plans = find_plans(legs)
        self.assertEqual(len(plans), 3)
        self.assertTrue(all(len(p) == 1 for p in plans))   # each a single segment (0 transfers)

    def test_orders_by_fewest_transfers(self):
        # "A" covers everything (0 transfers); "B" needs a change -> "A" option comes first
        legs = [{"A", "B"}, {"A"}]
        plans = find_plans(legs)
        self.assertEqual(plans[0], [("A", 0, 2)])

    def test_respects_limit(self):
        legs = [{"1", "2", "3", "4", "5"}]
        self.assertEqual(len(find_plans(legs, limit=2)), 2)

    def test_empty(self):
        self.assertEqual(find_plans([]), [])


# A trimmed SVG with two seats: 11 is taken ("Niedostepne"), 12 is free.
_SVG = (
    '<svg>'
    '<g aria-label="Miejsce 11 klasa 2, okno, Niedostepne, niewybrane"></g>'
    '<g aria-label="Miejsce 12 klasa 2, korytarz, niewybrane"></g>'
    '</svg>'
)


class ParseSeatsTests(SimpleTestCase):
    def test_reads_free_and_taken(self):
        seats = parser.parse_seats(_SVG)
        self.assertEqual(seats, [
            {"number": "11", "free": False},
            {"number": "12", "free": True},
        ])

    def test_seatless_svg_returns_empty(self):
        # A wagon with no numbered seats (e.g. a bistro car) is not an error.
        self.assertEqual(parser.parse_seats("<svg><g>bistro</g></svg>"), [])

    def test_changed_label_format_raises(self):
        # The SVG clearly is a seat map ("Miejsce" present) but no label matches -> format changed.
        broken = '<svg><g aria-label="Seat 11, class 2, window, unavailable"></g>Miejsce</svg>'
        with self.assertRaises(InterCityError):
            parser.parse_seats(broken)


class ClientErrorMappingTests(SimpleTestCase):
    def test_route_missing_keys_raises_intercity_error(self):
        # Upstream returned no "bledy" but a body without the expected route keys.
        with mock.patch.object(client, "_call_pociagi", return_value={"unexpected": True}):
            with self.assertRaises(InterCityError):
                client.get_route("6304", "2026-06-12 00:00:00", 5100069, 5100051)

    def test_connections_missing_keys_raises_intercity_error(self):
        with mock.patch.object(client, "_call_pociagi", return_value={"unexpected": True}):
            with self.assertRaises(InterCityError):
                client.search_connections(5100069, 5100051, "2026-06-12")
