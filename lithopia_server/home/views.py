from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from core.models import Dataset, RequestImage, ReferenceImage

# Create your views here.

TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"


def home(request):
    detected = RequestImage.objects.filter(detected=True).order_by('-dataset__acquisition_time')
    detected_last_stamp = detected[0].processed_stamp.strftime(TIMESTAMP_FORMAT)
    context = {
        "datasets_len": Dataset.objects.count(),
        "processed_len": RequestImage.objects.count(),
        "detected_len": detected.count(),
        "detected_last_stamp": detected_last_stamp,
        "processed_ratio": RequestImage.objects.count()/Dataset.objects.count()*100.0,
    }
    return render(request, 'home/home.html', context)