from django.db import models
from threading import Thread
import sentinel2


class Entry(models.Model):
    archive_path = models.TextField()
    download_stamp = models.DateTimeField()
    dataset_id = models.CharField(max_length=100)
    coords = models.TextField() # will store a JSON
    transformation = models.TextField() # will store a JSON
    wrapper = None

    @staticmethod
    def download_treaded(entry, overwrite=False):
        if Entry.wrapper is None:
            Entry.wrapper = sentinel2.sentinel_requests.DownloadWrapper(entry)
            Entry.wrapper.start_download(overwrite)
            return True
        else:
            return False # todo: handle this better

    @staticmethod
    def get_download_status():
        if Entry.wrapper is not None:
            return Entry.wrapper.get_progress()
        else:
            return None



