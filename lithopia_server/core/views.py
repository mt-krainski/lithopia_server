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
from matplotlib import pyplot as plt

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


def get_histogram(request, name):
    """
    Returns histogram for pixels selected with search_box from cropped image
        given by name
    :param request:
    :param name:
    :return:
    """
    processed_item = RequestImage.objects.filter(dataset__name=name)[0]
    image = Image.open(processed_item.image_path)
    box = json.loads(settings.search_box)
    bound_image = image.crop((
        box[0][0],
        box[0][1],
        box[1][0],
        box[1][1]))
    hist = np.array(bound_image.histogram())
    band_width = 256
    fig = Figure()
    fig.patch.set_visible(False)
    N = 8

    ax_red = fig.add_subplot(411)
    hist_red = hist[0:band_width]
    red_hist_plot = np.convolve(hist_red, np.ones((N,)) / N, mode='valid')
    ax_red.plot(red_hist_plot, color='red')
    ax_red.axis('off')

    ax_green = fig.add_subplot(412)
    hist_green = hist[band_width:(2*band_width)]
    green_hist_plot = np.convolve(hist_green, np.ones((N,)) / N, mode='valid')
    ax_green.plot(green_hist_plot, color='green')
    ax_green.axis('off')

    ax_blue = fig.add_subplot(413)
    hist_blue = hist[(band_width*2):(band_width*3)]
    blue_hist_plot = np.convolve(hist_blue, np.ones((N,)) / N, mode='valid')
    ax_blue.plot(blue_hist_plot, color='blue')
    ax_blue.axis('off')

    ax_blue = fig.add_subplot(414)
    hist_global = (hist_red + hist_green + hist_blue)/3
    global_hist_plot = np.convolve(hist_global, np.ones((N,)) / N, mode='valid')
    ax_blue.plot(global_hist_plot, color='black')
    ax_blue.axis('off')

    canvas = FigureCanvasAgg(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)
    response = HttpResponse(png_output.getvalue(), content_type='image/png')

    return response


def get_histogram_metrics(request, name):
    processed_item = RequestImage.objects.filter(dataset__name=name)[0]
    image = Image.open(processed_item.image_path)
    box = json.loads(settings.search_box)
    bound_image = image.crop((
        box[0][0],
        box[0][1],
        box[1][0],
        box[1][1]))
    hist = np.array(bound_image.histogram())
    band_width = 256
    hist_red = hist[0:band_width]
    hist_green = hist[band_width:(2 * band_width)]
    hist_blue = hist[(band_width * 2):(band_width * 3)]
    hist_global = (hist_red + hist_green + hist_blue) / 3
    log_hist = np.log(hist_global[hist_global!=0])
    metrics = {
        'mean': np.mean(hist_global),
        'std': np.std(hist_global),
        'median': np.median(hist_global),
        'geo_mean': np.exp(log_hist.sum()/len(log_hist))
    }

    return HttpResponse(
        json.dumps(metrics),
        'application/json'
    )

def create_reference(request):
    ReferenceImage.create_reference_task()
    return HttpResponse("Processing request...")


def get_diff_image(request, name):
    processed_item = RequestImage.objects.filter(dataset__name=name)[0]
    image = Image.open(processed_item.cropped_diff_image_path)
    response = HttpResponse(content_type="image/"+RequestImage.IMAGES_FORMAT)
    image.save(response, RequestImage.IMAGES_FORMAT)
    return response