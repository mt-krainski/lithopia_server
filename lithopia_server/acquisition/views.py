from django.http import HttpResponse
from django.shortcuts import render
from .models import Acquisition


# Create your views here.

def acquisition_page(request):
    return render(request,
                  'acquisition/acquisition_summary.html',
                  {'acquisition_list': Acquisition.objects.order_by('observation_time_start')})