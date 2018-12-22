import json
from datetime import datetime, date

from django.http import HttpResponse
from django.shortcuts import render
from pytz import utc

from .models import Acquisition


# Create your views here.
def datetime_parser(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()

def acquisition_page(request):
    return render(
        request,
      'acquisition/acquisition_summary.html',
      {'acquisition_list':
           Acquisition.objects.order_by('observation_time_start')})

def earliest(request):
    earliest = Acquisition.objects\
        .filter(observation_time_start__gt=datetime.now().replace(tzinfo=utc))\
        .order_by('observation_time_start')[0]

    return HttpResponse(
        json.dumps(earliest.observation_time_start, default=datetime_parser),
        'application/json'
    )