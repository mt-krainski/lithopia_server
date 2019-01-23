from django.core.management.base import BaseCommand
from core.models import Dataset, settings
import logging
from time import sleep

logging.basicConfig(format='[%(asctime)s] %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        logging.info("Removing archives...")
        for i in range(100):
            if not settings.processing_lock:
                break
            logging.info("Processing lock locked. retrying...")
            sleep(10)
        else:
            logging.error("Error. Lock remained locked.")

        try:
            settings.processing_lock = True
            Dataset.remove_archives()
        except Exception as e:
            logging.exception(e)
        finally:
            settings.processing_lock = False