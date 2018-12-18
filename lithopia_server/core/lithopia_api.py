
import requests
from datetime import datetime
from core.models import settings

FLAG_COLOR = "flagColor"
PLACE = "place"
REQUEST_TEMPLATE = {
    FLAG_COLOR: "",
    PLACE: {},
}

API_URL = "http://anonette.net:3000/api/Flagcolor"

def post_flagcolor(color, place=None):

    if place is None:
        place = {
            'lat': settings.target_lat,
            'lon': settings.target_lon,
        }

    request_dict = REQUEST_TEMPLATE.copy()
    request_dict[FLAG_COLOR] = color
    request_dict[PLACE] = place

    return requests.post(
        API_URL,
        request_dict
    )

