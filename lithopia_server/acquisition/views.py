import json
from datetime import datetime, date

from django.http import HttpResponse
from django.shortcuts import render
from pytz import utc

from .models import Acquisition


COUNT_MIN = 8

# Create your views here.
def datetime_parser(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()

def acquisition_page(request):
    past_acquisitions = Acquisition.objects\
        .filter(observation_time_start__lt=datetime.now().replace(tzinfo=utc))\
        .order_by('observation_time_start')
    past_count = past_acquisitions.count()
    past_additional_rows = max(0, COUNT_MIN - past_count)
    past_total_rows = past_count + past_additional_rows

    future_acquisitions = Acquisition.objects\
        .filter(observation_time_start__gt=datetime.now().replace(tzinfo=utc))\
        .order_by('observation_time_start')
    future_count = future_acquisitions.count()
    future_additional_rows = max(0, COUNT_MIN - future_count)
    future_total_rows = future_count+future_additional_rows

    return render(
        request,
      'acquisition/acquisition_summary.html',
      {'future_acquisitions': future_acquisitions,
       'future_total_rows': future_total_rows,
       'future_additional_rows_range': range(future_additional_rows),
       'past_acquisitions': past_acquisitions,
       'past_total_rows': past_total_rows,
       'past_additional_rows_range': range(past_additional_rows),
       })

def earliest(request):
    earliest = Acquisition.objects\
        .filter(observation_time_start__gt=datetime.now().replace(tzinfo=utc))\
        .order_by('observation_time_start')[0]

    return HttpResponse(
        json.dumps(
            {'earliest': earliest.observation_time_start},
            default=datetime_parser),
        'application/json'
    )