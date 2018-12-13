import cv2

from django.shortcuts import render

import matplotlib
matplotlib.use('Agg')

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
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.gridspec as gridspec

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
        'metrics': json.loads(summary_object.result_metrics)
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

    # plt.close(fig)

    return response


def create_reference(request):
    ReferenceImage.create_reference_task()
    return HttpResponse("Processing request...")


BARPLOT_Z_LIMIT = 100

def format_3d_barplot(ax):
    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    # make the grid lines transparent
    ax.xaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)
    ax.yaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)
    ax.zaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)

    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_zlim(0, BARPLOT_Z_LIMIT)


def get_diff_image(request, name):
    processed_item = RequestImage.objects.filter(dataset__name=name)[0]
    image = cv2.imread(processed_item.cropped_diff_image_path)
    fig = plt.figure(figsize=(12, 5))
    gs = gridspec.GridSpec(2, 3)
    plot_red = fig.add_subplot(gs[0,0], projection='3d')
    plot_green = fig.add_subplot(gs[0,1], projection='3d')
    plot_blue = fig.add_subplot(gs[1,0], projection='3d')
    plot_average = fig.add_subplot(gs[1,1], projection='3d')
    plot_image = fig.add_subplot(gs[:,2])
    ## todo: verify that the ravel procedure is necessary
    _x = range(0, image.shape[0])
    _y = range(0, image.shape[1])
    xx, yy = np.meshgrid(_x, _y)
    x, y = xx.ravel(), yy.ravel()
    bars_red = image[:,:,2].ravel()
    bars_red[bars_red > BARPLOT_Z_LIMIT] = BARPLOT_Z_LIMIT
    bars_green = image[:,:,1].ravel()
    bars_green[bars_green > BARPLOT_Z_LIMIT] = BARPLOT_Z_LIMIT
    bars_blue = image[:,:,0].ravel()
    bars_blue[bars_blue > BARPLOT_Z_LIMIT] = BARPLOT_Z_LIMIT
    bars_average = np.mean(image, axis=2).ravel()
    bars_average[bars_average > BARPLOT_Z_LIMIT] = BARPLOT_Z_LIMIT
    bottom = np.zeros_like(bars_red) # red, green, blue should be the same
    plot_red.bar3d(x, y, bottom, 1, 1, bars_red, shade=True, color='red')
    plot_green.bar3d(x, y, bottom, 1, 1, bars_green, shade=True, color='green')
    plot_blue.bar3d(x, y, bottom, 1, 1, bars_blue, shade=True, color='blue')
    plot_average.bar3d(x, y, bottom, 1, 1, bars_average, shade=True, color='white')
    plot_image.imshow(image[:,:,::-1])
    plot_image.axis('off')
    format_3d_barplot(plot_red)
    format_3d_barplot(plot_green)
    format_3d_barplot(plot_blue)
    format_3d_barplot(plot_average)

    plt.subplots_adjust(
        left=0.05,
        bottom=0.05,
        right=0.95,
        top=0.95,
        wspace=0.05,
        hspace=0.05)

    canvas = FigureCanvasAgg(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)

    response = HttpResponse(png_output.getvalue(), content_type='image/png')

    # plt.close(fig)

    return response