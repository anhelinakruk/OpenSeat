"""Tests for the seat-hopping algorithm (pure logic - no network, no database)."""
from django.test import SimpleTestCase

from trains.intercity.hopping import find_plan, fully_free_seats, seat_reach


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
