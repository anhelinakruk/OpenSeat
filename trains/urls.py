from django.urls import path
from . import api

urlpatterns = [
    path("api/stations/", api.station_view),
    path("api/connections/", api.connections_view),
    path("api/journey/", api.journey_view),
]