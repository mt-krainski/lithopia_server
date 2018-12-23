from django.core.management.base import BaseCommand
from acquisition.models import Acquisition
PYTHON_PROCESS_KEYWORD = 'python'
PROCESS_TASKS_KEYWORD = 'process_tasks'

MANAGE_SCRIPT = "manage.py"
PROCESS_TASKS = "process_tasks"

class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        Acquisition.update_acquisition_table()