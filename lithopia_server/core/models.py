from builtins import set
import datetime

from django.db import models

import dbsettings
from background_task import background
from sentinel2 import sentinel_requests
import sentinel2.images as sentinel_images
import sentinel2.transform as sentinel_transform
import os
import json
import math
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

class ApplicationSettings(dbsettings.Group):
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
    @background(schedule=5)
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
    def populate_acquisition_time():
        for dataset in Dataset.objects.all():
            manifest = sentinel_images.get_manifest(dataset.archive_path)
            time = sentinel_images.get_acquisition_time(manifest)
            dataset.acquisition_time = time
            dataset.save()

    @staticmethod
    def populate_dataset_name():
        for dataset in Dataset.objects.all():
            name = os.path.basename(dataset.archive_path).split('.')[0]
            dataset.name = name
            dataset.save()

    @staticmethod
    def populate_cloud_cover():
        for dataset in Dataset.objects.all():
            cloud_cover = sentinel_images.get_cloud_cover(dataset.archive_path)
            dataset.cloud_cover = cloud_cover
            dataset.save()


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
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)
    bounds = models.TextField()
    detected = models.BooleanField()
    image_path = models.CharField(max_length=1000)
    processed_stamp = models.DateTimeField(default=datetime.datetime.now)

    IMAGES_DIR = 'request_images'
    IMAGES_FORMAT = 'png'

    @staticmethod
    @background(schedule=10)
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

    def __str__(self):
        return self.dataset.name