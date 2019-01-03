from django.core.management.base import BaseCommand, CommandError
from core import tasks
import sys
import psutil
import subprocess
import os
import logging


from lithopia_server.settings import BASE_DIR

PYTHON_PROCESS_KEYWORD = 'python'
PROCESS_TASKS_KEYWORD = 'process_tasks'

MANAGE_SCRIPT = os.path.join(BASE_DIR, "manage.py")
PROCESS_TASKS = "process_tasks"

class Command(BaseCommand):
    help = 'Resets the tasks responsible for running dataset updates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            dest='reset',
            help='Cleans the tasks before issuing a new one',
        )

        parser.add_argument(
            '--kill',
            action='store_true',
            dest='kill',
            help='Cleans the tasks and kills all process_tasks processes',
        )

    def handle(self, *args, **options):

        process_tasks = self.get_process_tasks()

        if options['kill']:
            while process_tasks:
                process_tasks.kill()
                process_tasks = self.get_process_tasks()

            tasks.clean_perform_update()
            return

        if options['reset'] or not process_tasks:

            while process_tasks:
                process_tasks.kill()
                process_tasks = self.get_process_tasks()

            tasks.clean_perform_update()
            subprocess.Popen(
                [sys.executable, MANAGE_SCRIPT, PROCESS_TASKS],
            )

        tasks.add_update_task()

    @staticmethod
    def get_process_tasks():
        python_processes = [
            process for process in psutil.process_iter()
                    if PYTHON_PROCESS_KEYWORD in process.name()
        ]

        for p_process in python_processes:
            executable_name = [sys.executable]
            version = ".".join((str(sys.version_info[0]), str(sys.version_info[1])))
            if version in executable_name[0]:
                executable_name.append(executable_name[0].replace(version, ""))
            else:
                executable_name.append(executable_name[0]+version)
            if p_process.exe() in executable_name:
                if PROCESS_TASKS_KEYWORD in p_process.cmdline():
                    return p_process

        return False
