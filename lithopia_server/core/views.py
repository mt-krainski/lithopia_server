from django.shortcuts import render

from django.http import HttpResponse
from .models import RequestImage, settings, ReferenceImage
from PIL import Image, ImageDraw
from io import BytesIO
import os
from django.template import loader
import json
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np

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
    drawer = ImageDraw.Draw(image)
    search_box = tuple([tuple(val) for val in json.loads(settings.search_box)])
    drawer.rectangle(search_box, outline='red')
    response = HttpResponse(content_type="image/"+RequestImage.IMAGES_FORMAT)
    image.save(response, RequestImage.IMAGES_FORMAT)
    return response

def get_histogram(request, name):
    """
    Returns histogram for pixels selected with search_box from cropped image
        given by name
    :param request:
    :param name:
    :return:
    """
    file_path = os.path.join(RequestImage.IMAGES_DIR, name + "." + RequestImage.IMAGES_FORMAT)
    image = Image.open(file_path)
    box = json.loads(settings.search_box)
    bound_image = image.crop((
        box[0][0],
        box[0][1],
        box[1][0],
        box[1][1]))
    hist = bound_image.histogram()
    print(len(hist))
    print(bound_image.size)
    band_width = 256
    fig = Figure()
    fig.patch.set_visible(False)
    N = 8

    ax_red = fig.add_subplot(311)
    red_hist = np.convolve(hist[0:band_width], np.ones((N,)) / N, mode='valid')
    ax_red.plot(red_hist, color='red')
    ax_red.axis('off')

    ax_green = fig.add_subplot(312)
    green_hist = np.convolve(hist[band_width:(2*band_width)], np.ones((N,)) / N, mode='valid')
    ax_green.plot(green_hist, color='green')
    ax_green.axis('off')

    ax_blue = fig.add_subplot(313)
    blue_hist = np.convolve(hist[(band_width*2):(band_width*3)], np.ones((N,)) / N, mode='valid')
    ax_blue.plot(blue_hist, color='blue')
    ax_blue.axis('off')

    canvas = FigureCanvasAgg(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)
    response = HttpResponse(png_output.getvalue(), content_type='image/png')

    return response


def create_reference(request):
    ReferenceImage.create_reference_task()
    return HttpResponse("Processing request...")