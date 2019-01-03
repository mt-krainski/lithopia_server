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
PROCESS_TASKS = "process_tasks" # run for 3h max, cronjob is scheduled every 2 hrs
PROCESS_TASKS_ARGS = ["--duration", f"{3*60*60}"]

logging.basicConfig(format='[%(asctime)s] %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

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

        logging.debug("Starting script.")

        process_tasks = self.get_process_tasks()

        logging.debug(f"Got task: {process_tasks}")

        if options['kill']:
            logging.debug(f"Killing.")
            for instance in process_tasks:
                logging.debug(f"Task: {process_tasks}")
                instance.kill()

            logging.debug(f"Performing clean update")

            tasks.clean_perform_update()
            return

        if options['reset'] or not process_tasks:

            logging.debug(f"Resetting")

            logging.debug(f"Killing.")
            for instance in process_tasks:
                logging.debug(f"Task: {process_tasks}")
                instance.kill()

            logging.debug(f"Performing clean update")
            tasks.clean_perform_update()

            subprocess_command = [sys.executable, MANAGE_SCRIPT, PROCESS_TASKS] + PROCESS_TASKS_ARGS

            logging.debug(f"Running '{' '.join(subprocess_command)}'")
            subprocess.Popen(subprocess_command)

        logging.debug(f"Adding task")

        tasks.add_update_task()

    @staticmethod
    def get_process_tasks():

        logging.debug(f"Getting process_task instances")

        python_processes = [
            process for process in psutil.process_iter()
                    if PYTHON_PROCESS_KEYWORD in process.name()
        ]

        logging.debug(f"Found {len(python_processes)} python processes")

        process_tasks_exec = []

        for p_process in python_processes:
            executable_name = [sys.executable]
            version = ".".join((str(sys.version_info[0]), str(sys.version_info[1])))
            if version in executable_name[0]:
                executable_name.append(executable_name[0].replace(version, ""))
            else:
                executable_name.append(executable_name[0]+version)

            if p_process.exe() in executable_name:
                if PROCESS_TASKS_KEYWORD in p_process.cmdline():
                    process_tasks_exec.append(p_process)

        logging.debug(f"Found {len(process_tasks_exec)} process_task processes")

        return process_tasks_exec
