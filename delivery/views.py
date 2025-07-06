import requests
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from store.settings import NOVA_POSHTA_API_KEY


def search_city(city_name: str) -> JsonResponse:
    url = "https://api.novaposhta.ua/v2.0/json/"
    payload = {
        "apiKey": NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "searchSettlements",
        "methodProperties": {
            "CityName": city_name,
            "Limit": 10
        }
    }

    response = requests.post(url, json=payload)
    return response.json()

@csrf_exempt
@require_GET
def get_warehouses(request):
    city_ref = request.GET.get("city_ref", "").strip()
    if not city_ref:
        return JsonResponse([], safe=False)

    payload = {
        "apiKey": NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityRef": city_ref
        }
    }

    response = requests.post("https://api.novaposhta.ua/v2.0/json/", json=payload)
    data = response.json()

    if not data.get("success"):
        return JsonResponse([], safe=False)

    result = [
        {
            "label": wh["Description"],
            "ref": wh["Ref"]
        }
        for wh in data["data"]
    ]

    return JsonResponse(result, safe=False)

@csrf_exempt
@require_GET
def autocomplete_city(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse([], safe=False)

    cache_key = f"np_city_{query.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached, safe=False)

    payload = {
        "apiKey": NOVA_POSHTA_API_KEY,
        "modelName": "Address",
        "calledMethod": "searchSettlements",
        "methodProperties": {
            "CityName": query,
            "Limit": 10
        }
    }

    response = requests.post("https://api.novaposhta.ua/v2.0/json/", json=payload)
    data = response.json()

    if not data["success"]:
        return JsonResponse([], safe=False)

    result = [
        {
            "label": item["Present"],
            "ref": item.get("DeliveryCity") or item["Ref"]
        }
        for item in data["data"][0]["Addresses"]
        if item.get("DeliveryCity")
    ]

    cache.set(cache_key, result, timeout=60*60*12)
    return JsonResponse(result, safe=False)
