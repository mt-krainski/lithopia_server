from django.core.management.base import BaseCommand
from acquisition.models import Acquisition


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        Acquisition.update_acquisition_table()