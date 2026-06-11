"""Signal that prunes stale seat-map cache rows.

Why: the seat-map cache lives in the database (SeatMapCache), so without housekeeping the table
would grow forever and keep long-outdated availability. Whenever a fresh seat map is saved, this
post_save receiver deletes entries older than the staleness window.
"""
import logging
from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import SeatMapCache

logger = logging.getLogger("trains.cache")

# Seat maps older than this are useless (availability has long since changed); drop them on write.
STALE_AFTER = 3600  # seconds


@receiver(post_save, sender=SeatMapCache)
def prune_stale_seat_maps(sender, instance, **kwargs):
    cutoff = timezone.now() - timedelta(seconds=STALE_AFTER)
    deleted, _ = sender.objects.filter(fetched_at__lt=cutoff).delete()
    if deleted:
        logger.info("Pruned %d stale seat-map cache rows", deleted)
