from celery import shared_task
from .management.commands.seed_working_hours import Command
from .models import Doctor
from django.db.models import Count, Avg


@shared_task
def refresh_doctor_rating():
    # Annotate doctors with number of reviewers and average rating
    doctors_with_stats = Doctor.objects.annotate(
        reviewers_count=Count("reviews"), avg_rating=Avg("reviews__rating")
    )

    doctors_to_update = []

    for doctor in doctors_with_stats:
        # Average rating can be None if no reviews, handle that
        avg_rating = doctor.avg_rating or 0

        # Round to nearest integer if your model uses IntegerField
        doctor.rating = avg_rating
        doctor.reviewers_num = doctor.reviewers_count
        doctors_to_update.append(doctor)

    # Bulk update all doctors at once
    if doctors_to_update:
        Doctor.objects.bulk_update(doctors_to_update, ["rating", "reviewers_num"])


@shared_task
def generate_working_hours_task():
    command = Command()
    command.handle()

