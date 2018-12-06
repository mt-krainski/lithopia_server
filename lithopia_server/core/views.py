from django.shortcuts import render

from django.http import HttpResponse
from .models import RequestImage
from PIL import Image
import os
from datetime import datetime

from django.template import loader

HTML_DATE_FORMAT = '%d.%m.%Y %H:%M:%S'

def summary(request, id=0):
    template = loader.get_template('core/summary.html')
    summary_object = RequestImage.objects.order_by('-dataset__acquisition_time')[id]
    return HttpResponse(template.render({
        'dataset_name': summary_object.dataset.name,
        'id': id,
        'dataset_id': summary_object.dataset.dataset_id,
        'dataset_len': RequestImage.objects.count(),
        'acquistion_time': summary_object.dataset.acquisition_time.strftime(HTML_DATE_FORMAT),
        'processed_time': summary_object.processed_stamp.strftime(HTML_DATE_FORMAT),
        'marker' : summary_object.detected,
        'cloud_cover': f"{round(summary_object.dataset.cloud_cover, 2)} %",
    }, request))

def get_image(request, name):
    print(f"Opening file: {os.path.join(RequestImage.IMAGES_DIR, name+'.'+RequestImage.IMAGES_FORMAT)}")
    file_path = os.path.join(RequestImage.IMAGES_DIR, name+"."+RequestImage.IMAGES_FORMAT)
    # with open() as image_file:
    image = Image.open(file_path)
    response = HttpResponse(content_type="image/"+RequestImage.IMAGES_FORMAT)
    image.save(response, RequestImage.IMAGES_FORMAT)
    return response