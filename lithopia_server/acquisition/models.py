from django.db import models
from pytz import utc
from sentinel2.acquisition import get_acquisition_plan

from core.models import settings

# Create your models here.

class Acquisition(models.Model):
    polygon = models.TextField(help_text="WKT representation of the polygon") #wkt
    observation_time_start = models.DateTimeField()
    observation_time_stop = models.DateTimeField()
    name = models.CharField(max_length=100)
    swath_id = models.CharField(max_length=100)
    timeliness = models.CharField(max_length=100)
    station = models.CharField(max_length=100)
    mode = models.CharField(max_length=100)
    orbit_absolute = models.IntegerField()
    orbit_relative = models.IntegerField()
    scenes = models.IntegerField()
    observation_duration = models.IntegerField()
    satellite = models.CharField(max_length=100, default="")

    @staticmethod
    def update_acquisition_table():
        placemarks = get_acquisition_plan()
        matching_acquisitions = []
        location = (settings.target_lat, settings.target_lon)

        for placemark in placemarks:
            if placemark.is_point_in_polygon(lat=settings.target_lat, lon=settings.target_lon):
                matching_acquisitions.append(placemark)

        for acq in matching_acquisitions:
            if not Acquisition.objects.filter(swath_id=acq.ID):

                created_object = Acquisition(
                    polygon = acq.polygon.wkt,
                    observation_time_start = acq.ObservationTimeStart.replace(tzinfo=utc),
                    observation_time_stop = acq.ObservationTimeStop.replace(tzinfo=utc),
                    name = acq.name,
                    swath_id = acq.ID,
                    timeliness = acq.Timeliness,
                    station = acq.Station,
                    mode = acq.Mode,
                    orbit_absolute = int(acq.OrbitAbsolute),
                    orbit_relative = int(acq.OrbitRelative),
                    scenes = int(acq.Scenes),
                    observation_duration = int(acq.ObservationDuration),
                    satellite = acq.satellite
                )

                created_object.save()

    def __str__(self):
        time_format = "%Y.%m.%d %H:%M:%S"
        return f"{self.satellite} ({self.name}): {self.observation_time_start.strftime(time_format)}"