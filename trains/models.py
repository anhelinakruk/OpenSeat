from datetime import timedelta

from django.db import models
from django.utils import timezone


class SeatMapCache(models.Model):
    """Database-backed cache of a wagon's seat-map SVG for a single leg.

    Seat availability is the only volatile data we fetch from InterCity, so caching it in the
    database (rather than in local memory) lets the cache survive restarts and be shared across
    worker processes. Each row is one (train, wagon, leg, date) seat map plus when it was fetched.
    """
    category = models.CharField(max_length=8)
    number = models.CharField(max_length=10)
    wagon = models.CharField(max_length=8)
    dep_code = models.CharField(max_length=12)            # departure station 'e' code
    arr_code = models.CharField(max_length=12)            # arrival station 'e' code
    journey_date = models.CharField(max_length=8)         # YYYYMMDD
    svg = models.TextField()
    fetched_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "number", "wagon", "dep_code", "arr_code", "journey_date"],
                name="unique_seat_map_leg",
            )
        ]
        indexes = [models.Index(fields=["fetched_at"])]

    def __str__(self) -> str:
        return f"{self.category} {self.number} wagon {self.wagon} {self.dep_code}->{self.arr_code}"

    @classmethod
    def get_fresh(cls, *, category, number, wagon, dep_code, arr_code, journey_date, ttl):
        """Return the cached SVG if a row exists and is younger than ``ttl`` seconds, else None."""
        cutoff = timezone.now() - timedelta(seconds=ttl)
        row = cls.objects.filter(
            category=category, number=number, wagon=wagon,
            dep_code=dep_code, arr_code=arr_code, journey_date=journey_date,
            fetched_at__gte=cutoff,
        ).first()
        return row.svg if row else None

    @classmethod
    def store(cls, *, category, number, wagon, dep_code, arr_code, journey_date, svg):
        """Insert or refresh the cached SVG for this leg, stamped with the current time."""
        cls.objects.update_or_create(
            category=category, number=number, wagon=wagon,
            dep_code=dep_code, arr_code=arr_code, journey_date=journey_date,
            defaults={"svg": svg, "fetched_at": timezone.now()},
        )
