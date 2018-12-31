import os

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from sentinel2 import credentials

from core.models import Dataset, RequestImage, ReferenceImage, settings

# Create your views here.
from lithopia_server.settings import BASE_DIR

# TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"
TIMESTAMP_FORMAT = HTML_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S %Z'
USERNAME_TAG = "Copernicus_username"
PASSWORD_TAG = "Copernicus_password"

credentials.CREDENTIALS_FILE = os.path.join(BASE_DIR, credentials.CREDENTIALS_FILE)


def home(request):
    detected = RequestImage.objects.filter(detected=True).order_by('-dataset__acquisition_time')
    if detected:
        detected_last_stamp = detected[0].processed_stamp.strftime(TIMESTAMP_FORMAT)
    else:
        detected_last_stamp = None

    processed_ratio = RequestImage.objects.count()/Dataset.objects.count()*100.0 if Dataset.objects.count()!=0 else 0
    context = {
        "datasets_len": Dataset.objects.count(),
        "latest_dataset_stamp": Dataset.objects.order_by('-acquisition_time')[0].acquisition_time.strftime(TIMESTAMP_FORMAT),
        "processed_len": RequestImage.objects.count(),
        "detected_len": detected.count(),
        "detected_last_stamp": detected_last_stamp,
        "processed_ratio": processed_ratio,
        "lat": settings.target_lat,
        "lon": settings.target_lon,
    }
    return render(request, 'home/home.html', context)


@staff_member_required
def sentinel_credentials(request):
    return render(
        request,
        'home/sentinel_cred_form.html',
        {
            "username_tag": USERNAME_TAG,
            "password_tag": PASSWORD_TAG,
        })


@staff_member_required
def update_sentinel_credentials(request):
    username = request.POST[USERNAME_TAG]
    password = request.POST[PASSWORD_TAG]
    if credentials.test_credentials(username, password):
        credentials.store_credentials(username, password)
        return HttpResponse("Credentials updated")
    else:
        return HttpResponse("Credentinals not valid!")
