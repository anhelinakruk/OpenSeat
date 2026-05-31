"""REST API views: station autocomplete, connection list, journey plan."""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .intercity import client, finder, stations
from .intercity.errors import InterCityError


def _upstream_error(exc: InterCityError) -> Response:
    """Map an InterCity-side failure to a 502 with a readable message (instead of a raw 500)."""
    return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def station_view(request):
    """GET /api/stations/?q= - station autocomplete."""
    q = request.GET.get("q", "")
    try:
        return Response(stations.search(q))
    except InterCityError as exc:
        return _upstream_error(exc)


@api_view(["GET"])
def connections_view(request):
    """GET /api/connections/?from=&to=&date= - list of direct trains."""
    try:
        from_h = int(request.GET["from"])
        to_h = int(request.GET["to"])
        date = request.GET["date"]
    except (KeyError, ValueError):
        return Response({"error": "Required parameters: from, to, date."},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        return Response(client.search_connections(from_h, to_h, date))
    except InterCityError as exc:
        return _upstream_error(exc)


@api_view(["GET"])
def journey_view(request):
    """GET /api/journey/?category=&number=&departure=&from=&to=&date= - seats and transfers plan."""
    required = ("category", "number", "departure", "from", "to", "date")
    if any(request.GET.get(param) is None for param in required):
        return Response({"error": f"Required parameters: {', '.join(required)}."},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        result = finder.plan_journey(
            request.GET["category"], request.GET["number"], request.GET["departure"],
            request.GET["from"], request.GET["to"], request.GET["date"],
        )
        return Response(result)
    except InterCityError as exc:
        return _upstream_error(exc)
