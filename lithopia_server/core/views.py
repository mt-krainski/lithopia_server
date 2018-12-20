from datetime import datetime

import cv2

from django.shortcuts import render

import matplotlib
from pytz import utc

from core.tasks import UPDATE_TASK_NAME, update_datasets

matplotlib.use('Agg')

from django.http import HttpResponse
from .models import RequestImage, settings, ReferenceImage
from PIL import Image, ImageDraw
from io import BytesIO
import os
from django.template import loader
import json
from matplotlib.backends.backend_agg import FigureCanvasAgg
from django.contrib.admin.views.decorators import staff_member_required
from background_task.models import Task

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
        'marker': summary_object.detected,
        'cloud_cover': f"{round(summary_object.dataset.cloud_cover, 2)} %",
        'metrics': json.loads(summary_object.statistic_metrics),
        'marker_score': summary_object.template_match_score,
        'diff_score': json.loads(summary_object.diff_to_reference_score),
    }, request))


def get_image(request, name):
    processed_item = RequestImage.objects.filter(dataset__name=name)[0]
    print(f"Opening file: {processed_item.image_path}")
    # with open() as image_file:
    image = Image.open(processed_item.image_path)
    drawer = ImageDraw.Draw(image)
    search_box = tuple([tuple(val) for val in json.loads(settings.search_box)])
    drawer.rectangle(search_box, outline='red')
    response = HttpResponse(content_type="image/"+RequestImage.IMAGES_FORMAT)
    image.save(response, RequestImage.IMAGES_FORMAT)
    return response


def get_special_image(request, image_type, name):
    processed_item = RequestImage.objects.filter(dataset__name=name)[0]
    image_paths = {
        'histogram': processed_item.histogram_path,
        'diff': processed_item.diff_summary_path,
        'marker_score': processed_item.marker_score_path
    }

    image_path = image_paths.get(image_type)

    if image_path is not None:
        image = Image.open(image_path)
        response = HttpResponse(content_type="image/" + RequestImage.IMAGES_FORMAT)
        image.save(response, RequestImage.IMAGES_FORMAT)
        return response
    else:
        return None


@staff_member_required
def create_reference(request):
    ReferenceImage.create_reference_task()
    return HttpResponse("Processing request...")


def png_response(fig):
    canvas = FigureCanvasAgg(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)

    return HttpResponse(png_output.getvalue(), content_type='image/png')


def check_update_scheduled(request):
    result = {
        'check_update_scheduled' : None
    }

    tasks = Task.objects.filter(task_name=UPDATE_TASK_NAME)

    if tasks:
        perform_update_task = tasks[0]

        if not perform_update_task.locked_at:
            result['check_update_scheduled'] = True
        else:
            now = datetime.now()
            now = now.replace(tzinfo=utc)
            timediff = now - perform_update_task.locked_at

            if timediff > settings.update_task_timeout:
                result['check_update_scheduled'] = False
            else:
                result['check_update_scheduled'] = True
    else:
        result['check_update_scheduled'] = False

    return HttpResponse(json.dumps(result), content_type='application/json')


def reset_update_scheduled(request):
    for task in Task.objects.filter(task_name=UPDATE_TASK_NAME):
        task.delete()

    update_datasets()

    return HttpResponse("OK")
