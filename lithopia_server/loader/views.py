from django.shortcuts import render
import sentinel2
from django.template import loader
from django.http import HttpResponse
from .models import Entry

# Create your views here.
def index(request):
    template = loader.get_template('loader/main.html')
    return HttpResponse(template.render({}, request))


def quicklook(request):
    location = (float(request.GET['lat']), float(request.GET['lon']))
    max_cloud_cover = float(request.GET['cloud_cover'])

    sentinel_response = sentinel2.sentinel_requests.get_latest(location)
    entries = sentinel2.sentinel_requests.get_entries(sentinel_response)
    entry = sentinel2.sentinel_requests.get_latest_with_cloud_limit(entries, max_cloud_cover)
    thumbnail = sentinel2.sentinel_requests.quicklook(entry)
    response = HttpResponse(content_type="image/jpeg")
    thumbnail.save(response, 'jpeg')

    return response


def download_latest(request):
    location = (float(request.GET['lat']), float(request.GET['lon']))
    max_cloud_cover = float(request.GET['cloud_cover'])

    sentinel_response = sentinel2.sentinel_requests.get_latest(location)
    entries = sentinel2.sentinel_requests.get_entries(sentinel_response)
    entry = sentinel2.sentinel_requests.get_latest_with_cloud_limit(entries, max_cloud_cover)
    Entry.download_treaded(entry)

    return HttpResponse("OK")


def download_status(request):
    progress = Entry.get_download_status()
    return HttpResponse(progress)