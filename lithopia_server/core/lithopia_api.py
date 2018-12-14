
import requests
from datetime import datetime
from core.models import settings

FLAG_COLOR = "flagColor"
PLACE = "place"
TRANSACTION_ID = "transactionId"
TIMESTAMP = "timestamp"
REQUEST_TEMPLATE = {
    "$class": "org.lithopia.basic.Flagcolor",
    FLAG_COLOR: "",
    PLACE: {},
    TRANSACTION_ID: "",
    TIMESTAMP: ""
}

API_URL = "http://anonette.net:3000/api/Flagcolor"

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

def post_flagcolor(color, transaction_id, place=None):
    stamp = datetime.now()
    timestamp = stamp.strftime(TIMESTAMP_FORMAT)
    timestamp = timestamp[:-3] + "Z"

    if place is None:
        place = {
            'lat': settings.target_lat,
            'lon': settings.target_lon,
        }

    request_dict = REQUEST_TEMPLATE.copy()
    request_dict[FLAG_COLOR] = color
    request_dict[PLACE] = place
    request_dict[TRANSACTION_ID] = transaction_id
    request_dict[TIMESTAMP] = timestamp

    return requests.post(
        API_URL,
        request_dict
    )

