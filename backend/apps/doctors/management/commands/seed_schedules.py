import random
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.doctors.models import Doctor, Schedule, Days  # Replace 'myapp' with your actual app name

class Command(BaseCommand):
    help = "Generate fake schedules for doctors while ensuring no time overlaps"

    def add_arguments(self, parser):
        parser.add_argument(
            "--schedules_per_doctor",
            type=int,
            help="Number of schedules to create per doctor (default: random 1-3)",
        )

    def handle(self, *args, **options):
        # Check if the Django settings are in debug mode
        if not settings.DEBUG:
            raise CommandError("This command can only be run in DEBUG mode.")

        doctors = Doctor.objects.all()
        existing_schedules = Schedule.objects.values_list("doctor_id", flat=True)
        schedules_per_doctor = options["schedules_per_doctor"] or random.randint(1, 3)

        for doctor in doctors:
            if doctor.id in existing_schedules:
                self.stdout.write(self.style.WARNING(f"Skipping {doctor.user.full_name} (Schedule exists)"))
                continue

            work_days = random.sample(list(Days), k=random.randint(1, 3))  # Select 1-3 random workdays
            
            for day in work_days:
                schedules_created = 0
                day_schedules = []

                while schedules_created < schedules_per_doctor:
                    start_hour = random.randint(8, 14)  # Start between 8 AM - 2 PM
                    duration = random.randint(2, 4)  # 2 to 4 hours shift
                    start_time = datetime.time(start_hour, 0)
                    end_time = datetime.time(start_hour + duration, 0)

                    # Ensure no overlap
                    if all(not (s["start"] < end_time and start_time < s["end"]) for s in day_schedules):
                        Schedule.objects.create(
                            doctor=doctor,
                            day=day,
                            start_time=start_time,
                            end_time=end_time,
                            max_patients=random.randint(5, 10)
                        )
                        day_schedules.append({"start": start_time, "end": end_time})
                        schedules_created += 1

            self.stdout.write(self.style.SUCCESS(f"Created schedules for {doctor.user.full_name}"))

        self.stdout.write(self.style.SUCCESS("Fake schedules generated successfully!"))