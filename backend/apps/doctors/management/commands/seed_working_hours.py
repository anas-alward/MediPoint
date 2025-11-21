import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from apps.doctors.models import Schedule, WorkingHours

class Command(BaseCommand):
    help = "Generate working hours for the upcoming week based on schedules"

    def handle(self, *args, **kwargs):
    
        today = datetime.date.today()
        week_ahead = today + datetime.timedelta(days=7)

        for schedule in Schedule.objects.all():
            # Get all dates for the upcoming week's occurrence of this schedule
            for i in range(7):  # Loop through the next 7 days
                scheduled_date = today + datetime.timedelta(days=i)
                
                # Check if this is the correct weekday for the schedule
                if scheduled_date.strftime("%a").upper()[:3] == schedule.day:
                    start_datetime = make_aware(datetime.datetime.combine(scheduled_date, schedule.start_time))
                    end_datetime = make_aware(datetime.datetime.combine(scheduled_date, schedule.end_time))

                    # Avoid duplicate entries
                    if not WorkingHours.objects.filter(doctor=schedule.doctor, start_time=start_datetime).exists():
                        WorkingHours.objects.create(
                            doctor=schedule.doctor,
                            start_time=start_datetime,
                            end_time=end_datetime,
                            patient_left=schedule.max_patients
                        )

        self.stdout.write(self.style.SUCCESS("Successfully generated working hours for the next week."))
