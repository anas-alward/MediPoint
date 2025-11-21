from celery import shared_task
from .management.commands.seed_working_hours import Command

@shared_task
def generate_working_hours_task():
    command = Command()
    command.handle()
