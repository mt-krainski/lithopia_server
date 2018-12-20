from background_task import background
from background_task.models import Task

from core.models import Dataset, RequestImage


UPDATE_TASK_NAME = 'core.tasks.perform_update'


def add_update_task():
    if not Task.objects.filter(task_name=UPDATE_TASK_NAME):
        perform_update()


@background(schedule=1)
def perform_update():
    Dataset.get_lastest()
    RequestImage.process()
    RequestImage.resubmit_failed()


def clean_perform_update():
    for task in Task.objects.filter(task_name=UPDATE_TASK_NAME):
        task.delete()