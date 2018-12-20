from django.core.management.base import BaseCommand, CommandError
from core import tasks

class Command(BaseCommand):
    help = 'Resets the tasks responsible for running dataset updates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            dest='reset',
            help='Cleans the tasks before issuing a new one',
        )

    def handle(self, *args, **options):
        if options['reset']:
            tasks.clean_perform_update()

        tasks.add_update_task()