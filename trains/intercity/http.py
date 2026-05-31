import requests
from . import config

def get(url, extra_headers=None):
    headers = {**config.DEFAULT_HEADERS, **(extra_headers or {})}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response

def post(url, data=None, extra_headers=None):
    headers = {**config.DEFAULT_HEADERS, **(extra_headers or {})}
    response = requests.post(url, json=data, headers=headers, timeout=30)
    response.raise_for_status()
    return response