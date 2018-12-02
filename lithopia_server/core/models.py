from django.db import models

import dbsettings

class ApplicationSettings(dbsettings.Group):
    target_lat = dbsettings.FloatValue()
    target_lon = dbsettings.FloatValue()
    initial_download_size = dbsettings.PositiveIntegerValue()
    search_radius = dbsettings.FloatValue()


settings = ApplicationSettings("settings")


class Dataset(models.Model):
    archive_path = models.TextField()
    download_stamp = models.DateTimeField()
    dataset_id = models.CharField(max_length=100)
    coords = models.TextField() # will store a JSON
    transformation = models.TextField() # will store a JSON
    wrapper = None