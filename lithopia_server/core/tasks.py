from background_task import background
from background_task.models import Task

from core.models import Dataset, RequestImage

UPDATE_TASK_NAME = 'core.tasks.perform_update'


@background(schedule=1)
def update_datasets():
    if not Task.objects.filter(task_name=UPDATE_TASK_NAME):
        perform_update(repeat=Task.HOURLY)


@background(schedule=1)
def perform_update():
    Dataset.get_lastest()
    RequestImage.process()
    RequestImage.resubmit_failed()