from django.http import HttpResponse
from django.shortcuts import render
from .models import Acquisition


# Create your views here.

def acquisition_page(request):
    Acquisition.update_acquisition_table()
    return HttpResponse("OK")