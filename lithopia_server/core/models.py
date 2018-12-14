from builtins import set
import datetime

from PIL import Image
from django.db import models

import matplotlib

matplotlib.use('Agg')

import dbsettings
from background_task import background
from sentinel2 import sentinel_requests
import sentinel2.images as sentinel_images
import sentinel2.transform as sentinel_transform
from sentinel2 import image_analysis
import os
import json
import math
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.gridspec as gridspec
from time import sleep
import cv2

class ApplicationSettings(dbsettings.Group):
    name = dbsettings.TextValue()
    target_lat = dbsettings.FloatValue()
    target_lon = dbsettings.FloatValue()
    initial_download_size = dbsettings.PositiveIntegerValue()
    search_radius = dbsettings.FloatValue()
    initial_download_running = dbsettings.BooleanValue(default=False)
    search_box = dbsettings.TextValue(default=None)
    cloud_cover_limit = dbsettings.FloatValue(default=0.0)
    barplot_z_limit = dbsettings.FloatValue(default=100.0)
    match_threshold = dbsettings.FloatValue(default=30.0)
    flag_color = dbsettings.TextValue(default='red')


settings = ApplicationSettings("Core")


class Dataset(models.Model):
    archive_path = models.TextField()
    name = models.CharField(max_length=100, default=" ")
    download_stamp = models.DateTimeField(auto_now_add=True)
    dataset_id = models.CharField(max_length=100)
    coords = models.TextField() # will store a JSON
    transformation = models.TextField() # will store a JSON
    acquisition_time = models.DateTimeField()
    cloud_cover = models.FloatField(default=None, blank=True, null=True)
    wrapper = None

    @staticmethod
    @background(schedule=1)
    def get_lastest():
        print("Getting latest data set")
        try:
            print(f"Current size: {Dataset.objects.count()}")
            if settings.initial_download_size > Dataset.objects.count():
                print(f"Getting: {settings.initial_download_size-Dataset.objects.count()} objects")
            while True:
                if not settings.initial_download_running:
                    settings.initial_download_running = True
                    if settings.target_lat is not None and settings.target_lon is not None:
                        location = (settings.target_lat, settings.target_lon)
                        response = sentinel_requests.get_latest(location)
                        entries = sentinel_requests.get_entries(response)
                        for entry in entries:
                            if not Dataset.objects.filter(dataset_id=entry['id']).exists():
                                print("Getting latest")
                                dataset_name = sentinel_requests.download(entry, True)
                                archive_path = os.path.join(sentinel_requests.DATA_PATH, dataset_name+sentinel_requests.ARCHIVE_EXT)
                                manifest = sentinel_images.get_manifest(archive_path)
                                time = sentinel_images.get_acquisition_time(manifest)
                                coords = sentinel_images.get_coordinates(manifest)
                                image = sentinel_images.get_tci_image(archive_path)
                                transormation = sentinel_transform.find_transform(
                                        coords,
                                        sentinel_transform.get_image_boundries(image, image.size)
                                )
                                cloud_cover = sentinel_images.get_cloud_cover(archive_path)
                                db_entry = Dataset(
                                    archive_path = archive_path,
                                    dataset_id = entry['id'],
                                    coords = json.dumps(coords),
                                    transformation = json.dumps(transormation.tolist()),
                                    acquisition_time=time,
                                    cloud_cover=cloud_cover,
                                    name=dataset_name,
                                )
                                db_entry.save()
                            if Dataset.objects.count() >= settings.initial_download_size:
                                break
                if Dataset.objects.count() >= settings.initial_download_size:
                    break
                sleep(10)

        finally:
            settings.initial_download_running = False
            Dataset.remove_non_referenced()


    @staticmethod
    def remove_non_referenced():
        stored_files = os.listdir(sentinel_requests.DATA_PATH)
        known_files = [item['archive_path'] for item in Dataset.objects.values('archive_path')]
        files_to_remove = [file for file in stored_files if
                           os.path.join(sentinel_requests.DATA_PATH, file) not in known_files]

        for file in files_to_remove:
            os.remove(os.path.join(sentinel_requests.DATA_PATH, file))

    @staticmethod
    def get_dataset_name(dataset):
        return os.path.basename(dataset.archive_path).split(sentinel_requests.ARCHIVE_EXT)[0]

    def __str__(self):
        return self.name


class RequestImage(models.Model):
    dataset = models.OneToOneField(
        Dataset,
        on_delete=models.CASCADE,
        primary_key=True)
    bounds = models.TextField()
    detected = models.BooleanField(default=False)
    submitted = models.BooleanField(default=False)
    image_path = models.CharField(max_length=1000)
    cropped_diff_image_path = models.CharField(max_length=1000, default="")
    histogram_path = models.CharField(max_length=1000, default="")
    diff_summary_path = models.CharField(max_length=1000, default="")
    marker_score_path = models.CharField(max_length=1000, default="")
    processed_stamp = models.DateTimeField(default=datetime.datetime.now)
    statistic_metrics = models.TextField(default="") #json
    template_match_score = models.FloatField(default=0)
    diff_to_reference_score = models.TextField(default="") #json

    IMAGES_DIR = 'request_images'
    PROCESSED_DIR = os.path.join(IMAGES_DIR, "processed_raw")
    HISTOGRAM_DIR = os.path.join(IMAGES_DIR, "histogram")
    DIFF_DIR = os.path.join(IMAGES_DIR, "processed")
    MARKER_SCORE_DIR = os.path.join(IMAGES_DIR, "markers")
    IMAGES_FORMAT = 'png'

    @staticmethod
    @background(schedule=1)
    def process():
        not_processed = Dataset.objects.filter(requestimage=None)
        print(f"Processing {len(not_processed)} images")
        bounds = {
            'upper': RequestImage.distance_to_lat_lon(
                (settings.target_lon, settings.target_lat),
                settings.search_radius,
                math.radians(0))[1],
            'lower': RequestImage.distance_to_lat_lon(
                (settings.target_lon, settings.target_lat),
                settings.search_radius,
                math.radians(180))[1],
            'right': RequestImage.distance_to_lat_lon(
                (settings.target_lon, settings.target_lat),
                settings.search_radius,
                math.radians(90))[0],
            'left': RequestImage.distance_to_lat_lon(
                (settings.target_lon, settings.target_lat),
                settings.search_radius,
                math.radians(270))[0]
        }

        for dataset in not_processed:
            t_function = sentinel_transform.transform_function(np.array(json.loads(dataset.transformation)))
            image = sentinel_images.get_tci_image(dataset.archive_path)
            cropped_image = sentinel_images.crop_by_coords(bounds, image, t_function)
            name = Dataset.get_dataset_name(dataset) + '.' + RequestImage.IMAGES_FORMAT
            if not os.path.exists(RequestImage.IMAGES_DIR):
                os.makedirs(RequestImage.IMAGES_DIR)

            path = os.path.join(RequestImage.IMAGES_DIR, name)
            plt.imsave(path, cropped_image, format=RequestImage.IMAGES_FORMAT)
            new_object = RequestImage(
                dataset = dataset,
                bounds = json.dumps(bounds),
                detected = False,
                image_path = path,
                processed_stamp = datetime.datetime.now(datetime.timezone.utc)
            )
            new_object.save()
            new_object.process_metrics()
            new_object.process_histogram()
            new_object.diff_to_reference()
            new_object.process_diff_plot()
            new_object.process_marker_plot()


    @staticmethod
    def distance_to_lat_lon(initial_pos, distance, heading):
        """
        :param initial_pos: (lon, lat)
        :param distance: distance traveled [km]
        :param heading: direction of travel (CW from North) [rad]
        :return: (lon, lat)
        """
        lon = math.radians(initial_pos[0])
        lat = math.radians(initial_pos[1])
        earth_radius = 6371
        lat_final = math.asin(math.sin(lat) * math.cos(distance / earth_radius) +
                       math.cos(lat) * math.sin(distance / earth_radius) * math.cos(heading))
        lon_final = lon + math.atan2(math.sin(heading) * math.sin(distance / earth_radius) * math.cos(lat),
                             math.cos(distance / earth_radius) - math.sin(lat) * math.sin(lat_final))

        return math.degrees(lon_final), math.degrees(lat_final)

    @staticmethod
    def get_cropped(image):
        box = json.loads(settings.search_box)
        return image.crop((box[0][0], box[0][1],
                           box[1][0], box[1][1]))

    @staticmethod
    def get_cropped_cv(image):
        box = json.loads(settings.search_box)
        return image[box[0][1]:box[1][1], box[0][0]:box[1][0]]

    @staticmethod
    def normlize_cv_image(image):
        for ch in range(3):
            image[:, :, ch] -= np.min(image[:, :, ch])
            image[:, :, ch] = \
                (255 * image[:, :, ch].astype(np.float64)
                 / np.max(image[:, :, ch])).astype(np.uint8)

        return image

    def diff_to_reference(self):
        ref_item = ReferenceImage.objects.filter(name=settings.name)
        if not ref_item:
            ReferenceImage.create_reference_image()
            ref_item = ReferenceImage.objects.filter(name=settings.name)
            if not ref_item:
                raise ValueError("Unable to create reference image")

        ref_item = ref_item[0]

        ref_image = cv2.imread(ref_item.image_path)
        self_image = cv2.imread(self.image_path)
        offset = image_analysis.get_offset(self_image, ref_image)
        print(offset)
        ref_image = image_analysis.offset_image(ref_image, offset)
        cropped_ref_image = RequestImage.get_cropped_cv(ref_image)
        cropped_self_image = RequestImage.get_cropped_cv(self_image)

        diff = image_analysis.get_image_difference(
            cropped_ref_image,
            cropped_self_image )

        if not os.path.exists(RequestImage.PROCESSED_DIR):
            os.makedirs(RequestImage.PROCESSED_DIR)

        image_path = os.path.join(
            RequestImage.PROCESSED_DIR,
            f"{self.dataset.name}.{RequestImage.IMAGES_FORMAT}")
        cv2.imwrite(image_path, diff)
        self.cropped_diff_image_path = image_path
        self.save()

    def __str__(self):
        return self.dataset.name

    def process_metrics(self):
        image = cv2.imread(self.image_path)
        bound_image = RequestImage.get_cropped_cv(image)
        image_averaged = np.mean(bound_image, axis=2)
        metrics = {
            'mean': np.mean(image_averaged),
            'std': np.std(image_averaged),
            'median': np.median(image_averaged),
            'geo_mean': np.exp(np.log(image_averaged).sum() / len(image_averaged))
        }
        self.statistic_metrics = json.dumps(metrics)
        self.save()

    def process_histogram(self):
        hist_figure = self.histogram_plot()

        if not os.path.exists(RequestImage.HISTOGRAM_DIR):
            os.makedirs(RequestImage.HISTOGRAM_DIR)

        image_path = os.path.join(
            RequestImage.HISTOGRAM_DIR,
            f"{self.dataset.name}.{RequestImage.IMAGES_FORMAT}")

        hist_figure.savefig(image_path)
        plt.close(hist_figure)
        self.histogram_path = image_path
        self.save()

    def process_diff_plot(self):
        diff_figure = self.diff_plot()

        if not os.path.exists(RequestImage.DIFF_DIR):
            os.makedirs(RequestImage.DIFF_DIR)

        image_path = os.path.join(
            RequestImage.DIFF_DIR,
            f"{self.dataset.name}.{RequestImage.IMAGES_FORMAT}")

        diff_figure.savefig(image_path)
        plt.close(diff_figure)
        self.diff_summary_path = image_path
        self.save()

    @staticmethod
    def format_3d_barplot(ax, barplot_limit=None):
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        # make the grid lines transparent
        ax.xaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)
        ax.yaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)
        ax.zaxis._axinfo["grid"]['color'] = (1, 1, 1, 0)

        ax.set_xticks([])
        ax.set_yticks([])
        if barplot_limit is not None:
            ax.set_zlim(0, barplot_limit)

    @staticmethod
    def make_3d_bar_plot(ax, data, color="blue", limit=None, format=False):
        _x = range(0, data.shape[0])
        _y = range(0, data.shape[1])
        xx, yy = np.meshgrid(_x, _y)
        x, y = xx.ravel(), yy.ravel()
        data_r = data.ravel()
        bottom = np.zeros_like(data_r)
        if limit is not None:
            data_r[data_r > limit] = limit

        ax.bar3d(x, y, bottom, 1, 1, data_r, shade=True, color=color)

        if format:
            RequestImage.format_3d_barplot(ax, limit)


    def get_diff_score(self):
        image = cv2.imread(self.cropped_diff_image_path)
        score_red = np.max(image[:, :, 2]) / np.mean(image[:, :, 2])
        score_green = np.max(image[:, :, 1]) / np.mean(image[:, :, 1])
        score_blue = np.max(image[:, :, 0]) / np.mean(image[:, :, 0])
        image_mean = np.mean(image, axis=2)
        score_mean = np.max(image_mean) / np.mean(image_mean)

        self.diff_to_reference_score = json.dumps(
            [score_red, score_green, score_blue, score_mean]
        )
        self.save()

    def diff_plot(self):
        image = cv2.imread(self.cropped_diff_image_path)
        fig = plt.figure(figsize=(12, 5))
        gs = gridspec.GridSpec(2, 3)
        plot_red = fig.add_subplot(gs[0, 0], projection='3d')
        plot_green = fig.add_subplot(gs[0, 1], projection='3d')
        plot_blue = fig.add_subplot(gs[1, 0], projection='3d')
        plot_average = fig.add_subplot(gs[1, 1], projection='3d')
        plot_image = fig.add_subplot(gs[:, 2])
        ## todo: verify that the ravel procedure is necessary
        self.make_3d_bar_plot(plot_red, image[:, :, 2],
                              'red', settings.barplot_z_limit, True)
        self.make_3d_bar_plot(plot_green, image[:, :, 1],
                              'green', settings.barplot_z_limit, True)
        self.make_3d_bar_plot(plot_blue, image[:, :, 0],
                              'blue', settings.barplot_z_limit, True)
        self.make_3d_bar_plot(plot_average, np.mean(image, axis=2),
                              'white', settings.barplot_z_limit, True)

        plot_image.imshow(image[:, :, ::-1])
        plot_image.axis('off')

        fig.subplots_adjust(
            left=0.05,
            bottom=0.05,
            right=0.95,
            top=0.95,
            wspace=0.05,
            hspace=0.05)

        return fig

    def histogram_plot(self):
        image = Image.open(self.image_path)
        box = json.loads(settings.search_box)
        bound_image = image.crop((
            box[0][0],
            box[0][1],
            box[1][0],
            box[1][1]))
        hist = np.array(bound_image.histogram())
        band_width = 256
        fig = plt.figure()
        fig.patch.set_visible(False)
        N = 8

        ax_red = fig.add_subplot(411)
        hist_red = hist[0:band_width]
        red_hist_plot = np.convolve(hist_red, np.ones((N,)) / N, mode='valid')
        ax_red.plot(red_hist_plot, color='red')
        ax_red.axis('off')

        ax_green = fig.add_subplot(412)
        hist_green = hist[band_width:(2 * band_width)]
        green_hist_plot = np.convolve(hist_green, np.ones((N,)) / N, mode='valid')
        ax_green.plot(green_hist_plot, color='green')
        ax_green.axis('off')

        ax_blue = fig.add_subplot(413)
        hist_blue = hist[(band_width * 2):(band_width * 3)]
        blue_hist_plot = np.convolve(hist_blue, np.ones((N,)) / N, mode='valid')
        ax_blue.plot(blue_hist_plot, color='blue')
        ax_blue.axis('off')

        ax_blue = fig.add_subplot(414)
        hist_global = (hist_red + hist_green + hist_blue) / 3
        global_hist_plot = np.convolve(hist_global, np.ones((N,)) / N, mode='valid')
        ax_blue.plot(global_hist_plot, color='black')
        ax_blue.axis('off')

        return fig

    def process_marker_plot(self):
        if not os.path.exists(RequestImage.MARKER_SCORE_DIR):
            os.makedirs(RequestImage.MARKER_SCORE_DIR)

        marker_score_figure = self.marker_plot()

        image_path = os.path.join(
            RequestImage.MARKER_SCORE_DIR,
            f"{self.dataset.name}.{RequestImage.IMAGES_FORMAT}")

        marker_score_figure.savefig(image_path)
        plt.close(marker_score_figure)
        self.marker_score_path = image_path
        self.save()

    def match_marker(self):
        image = cv2.imread(self.cropped_diff_image_path)
        template_path = ReferenceImage.objects.filter(name=settings.name)[0].marker_path
        template = cv2.imread(template_path)

        matching_result = cv2.matchTemplate(image, template,
                                            cv2.TM_CCORR_NORMED)

        self.template_match_score = np.max(matching_result)

        if self.template_match_score > settings.match_threshold:
            self.detected = True
        else:
            self.detected = False

        return matching_result

    def marker_plot(self):
        marker_scores = self.match_marker()
        color = 'white'
        fig = plt.figure(figsize=(5, 5))

        ax = fig.add_subplot(111, projection='3d')
        self.make_3d_bar_plot(ax, marker_scores,
                              color, None, True)
        return fig

    def submit(self):
        from core import lithopia_api
        result = lithopia_api.post_flagcolor(
            settings.flag_color,
            self.dataset.name,
        )
        if result.status_code == 200:
            self.submitted = True

    @staticmethod
    def resubmit_failed():
        for item in RequestImage.objects.filter(submitted=False):
            item.submit()


class ReferenceImage(models.Model):
    used_datasets = models.ManyToManyField(Dataset)
    DIR = 'reference'
    marker_path = models.CharField(max_length=1000, default="")
    image_path = models.CharField(max_length=1000)
    name = models.CharField(max_length=100, unique=True)

    @staticmethod
    def create_reference_image():
        valid_datasets = Dataset.objects.filter(cloud_cover__lte=settings.cloud_cover_limit)
        print(f"Creating reference from {len(valid_datasets)} datasets")
        reference = valid_datasets[0]
        reference_image = cv2.imread(reference.requestimage.image_path)
        final_image = reference_image/len(valid_datasets)

        for dataset in valid_datasets[1:]:
            image = cv2.imread(dataset.requestimage.image_path)
            offset = image_analysis.get_offset(reference_image, image)
            print(f"offset: {offset}")
            image_offset = image_analysis.offset_image(image, offset)
            final_image = cv2.add(final_image, image_offset/len(valid_datasets))

        print("Storing result")
        if not os.path.exists(ReferenceImage.DIR):
            os.makedirs(ReferenceImage.DIR)

        image_path = os.path.join(ReferenceImage.DIR, f"{settings.name}.{RequestImage.IMAGES_FORMAT}")

        cv2.imwrite(image_path, final_image)

        existing = ReferenceImage.objects.filter(name=settings.name)

        if existing:
            existing[0].image_path = image_path
            existing[0].used_datasets.clear()
            for dataset in valid_datasets:
                existing[0].used_datasets.add(dataset)
        else:
            reference_object = ReferenceImage(
                image_path=image_path,
                name=settings.name)
            reference_object.save()
            for dataset in valid_datasets:
                reference_object.used_datasets.add(dataset)
            reference_object.save()

        print("Task Completed")
        print("Resetting scores")
        for item in RequestImage.objects.all():
            item.diff_to_reference()
            item.process_diff_plot()
            item.get_diff_score()
            item.process_marker_plot()

        print("Task Completed")

    @staticmethod
    @background(schedule=1)
    def create_reference_task():
        ReferenceImage.create_reference_image()

    def __str__(self):
        return self.name


