from django.shortcuts import render

from django.http import HttpResponse
from .models import RequestImage
from PIL import Image
import os


from django.template import loader

def summary(request):
    template = loader.get_template('core/summary.html')
    latest = RequestImage.objects.latest('dataset__acquisition_time')
    return HttpResponse(template.render({'dataset_name': latest.dataset.name}, request))

def get_image(request, name):
    print(f"Opening file: {os.path.join(RequestImage.IMAGES_DIR, name+'.'+RequestImage.IMAGES_FORMAT)}")
    file_path = os.path.join(RequestImage.IMAGES_DIR, name+"."+RequestImage.IMAGES_FORMAT)
    # with open() as image_file:
    image = Image.open(file_path)
    response = HttpResponse(content_type="image/"+RequestImage.IMAGES_FORMAT)
    image.save(response, RequestImage.IMAGES_FORMAT)
    return response