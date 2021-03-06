
import requests
from core.models import settings

FLAG_COLOR = "flagColor"
PLACE = "place"
REQUEST_SOURCE = "requestSource"
DATASET_ID = "datasetId"
REQUEST_TEMPLATE = {
    FLAG_COLOR: "",
    PLACE: {},
    REQUEST_SOURCE: "lithopia_server",
    DATASET_ID: "",
}

API_URL = "http://anonette.net:3000/api/Flagcolor"

def post_flagcolor(color, dataset_id, place=None):

    if place is None:
        place = {
            'lat': settings.target_lat,
            'lon': settings.target_lon,
        }

    request_dict = REQUEST_TEMPLATE.copy()
    request_dict[FLAG_COLOR] = color
    request_dict[PLACE] = place
    request_dict[DATASET_ID] = dataset_id

    return requests.post(
        API_URL,
        request_dict
    )

