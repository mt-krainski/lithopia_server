from builtins import set
import datetime

from PIL import Image
from django.db import models

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
from time import sleep
import cv2
from django.contrib.admin.views.decorators import staff_member_required

class ApplicationSettings(dbsettings.Group):
    name = dbsettings.TextValue()
    target_lat = dbsettings.FloatValue()
    target_lon = dbsettings.FloatValue()
    initial_download_size = dbsettings.PositiveIntegerValue()
    search_radius = dbsettings.FloatValue()
    initial_download_running = dbsettings.BooleanValue(default=False)
    search_box = dbsettings.TextValue(default=None)
    cloud_cover_limit = dbsettings.FloatValue(default=0.0)


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
            if settings.initial_download_size < Dataset.objects.count():
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
    detected = models.BooleanField()
    image_path = models.CharField(max_length=1000)
    cropped_diff_image_path = models.CharField(max_length=1000, default="")
    processed_stamp = models.DateTimeField(default=datetime.datetime.now)
    result_metrics = models.TextField(default="") #json

    IMAGES_DIR = 'request_images'
    PROCESSED_DIR = os.path.join(IMAGES_DIR, "processed")
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
            new_object.diff_to_reference()
            new_object.process_metrics()


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
        self.result_metrics = json.dumps(metrics)
        self.save()


class ReferenceImage(models.Model):
    used_datasets = models.ManyToManyField(Dataset)
    DIR = 'reference'
    image_path = models.CharField(max_length=100)
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

    @staticmethod
    @staff_member_required
    @background(schedule=1)
    def create_reference_task():
        ReferenceImage.create_reference_image()

    def __str__(self):
        return self.name


