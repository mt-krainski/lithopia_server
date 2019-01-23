from background_task import background
from background_task.models import Task
import logging
from time import sleep

from core.models import Dataset, RequestImage, settings

logging.basicConfig(format='[%(asctime)s] %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

UPDATE_TASK_NAME = 'core.tasks.perform_update'


def add_update_task():
    if not Task.objects.filter(task_name=UPDATE_TASK_NAME):
        perform_update()


@background(schedule=1)
def perform_update():
    for i in range(100):
        if not settings.processing_lock:
            break
        logging.info("Processing lock locked. retrying...")
        sleep(10)
    else:
        logging.error("Error. Lock remained locked.")

    try:
        settings.processing_lock = True
        Dataset.get_lastest()
        RequestImage.process()
        RequestImage.resubmit_failed()
    except Exception as e:
        logging.exception(e)
    finally:
        settings.processing_lock = False


def clean_perform_update():
    for task in Task.objects.filter(task_name=UPDATE_TASK_NAME):
        task.delete()