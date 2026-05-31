from rest_framework.decorators import api_view
from rest_framework.response import Response
from .intercity import stations, client, finder

@api_view(['GET'])
def station_view(request):
    q = request.GET.get("q", "")
    results = stations.search(q)
    return Response(results)

@api_view(["GET"])
def connections_view(request):
    from_h = int(request.GET.get("from"))   
    to_h = int(request.GET.get("to"))        
    date = request.GET.get("date")           
    trains = client.search_connections(from_h, to_h, date)
    return Response(trains)

@api_view(["GET"])
def journey_view(request):
    result = finder.plan_journey(
        request.GET.get("category"),   # IC
        request.GET.get("number"),     # 8331
        request.GET.get("departure"),  # 2026-06-01T08:10:00
        request.GET.get("from"),       # kod h stacji odjazdu
        request.GET.get("to"),         # kod h stacji przyjazdu
        request.GET.get("date"),       # 20260601
    )
    return Response(result)