import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import make_password
from django.core.files import File
from django.conf import settings
from django.db import transaction
from apps.users.models import User
from apps.doctors.models import Doctor, Specialty, Schedule, WorkingHours, Days
from datetime import time, datetime, timedelta
from django.utils.timezone import make_aware


class Command(BaseCommand):
    help = "Seed doctors with related data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing doctors before seeding",
        )
        parser.add_argument(
            "--data-file",
            type=str,
            default="apps/doctors/fixtures/doctors/profile.json",
            help="Path to doctors JSON data file",
        )
        parser.add_argument(
            "--images-dir",
            type=str,
            default="apps/doctors/fixtures/doctors/images",
            help="Directory containing doctor profile images",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command can only be run in DEBUG mode.")

        data_file_path = settings.BASE_DIR / options["data_file"]
        images_dir = settings.BASE_DIR / options["images_dir"]

        try:
            with open(data_file_path, "r") as f:
                doctors_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"Doctors data file not found at: {data_file_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in doctors file: {e}")

        if options["clear"]:
            self.clear_doctors()

        self.seed_doctors(doctors_data, images_dir)

    def clear_doctors(self):
        """Clear existing doctors and related data"""
        self.stdout.write("Clearing existing doctors and related data...")

        # Delete in correct order to handle foreign key constraints
        WorkingHours.objects.all().delete()
        Schedule.objects.all().delete()
        Doctor.objects.all().delete()

        # Delete only doctor users (be careful with this in production)
        User.objects.filter(email__startswith="doctor").delete()

        self.stdout.write("✓ Cleared all doctors data")

    def get_profile_image(self, image_name, images_dir):
        """Get profile image file"""
        if not image_name:
            return None

        image_path = images_dir / f"{image_name}.jpg"

        # Try different extensions
        extensions = [".jpg", ".jpeg", ".png", ".webp"]
        for ext in extensions:
            test_path = images_dir / f"{image_name}{ext}"
            print(test_path)
            if os.path.exists(test_path):
                image_path = test_path
                break

        if not os.path.exists(image_path):
            self.stdout.write(
                self.style.WARNING(f"Profile image not found: {image_name}")
            )
            return None

        try:
            return File(open(image_path, "rb"), name=os.path.basename(image_path))
        except IOError as e:
            self.stdout.write(
                self.style.WARNING(f"Could not open image file: {image_path} - {e}")
            )
            return None

    def seed_doctors(self, doctors_data, images_dir):
        """Create doctors with all related data"""
        self.stdout.write("Seeding doctors...")

        created_count = 0
        updated_count = 0

        for doctor_data in doctors_data:
            try:
                with transaction.atomic():
                    # Create or get user
                    user = self.create_doctor_user(doctor_data)

                    # Get specialty
                    specialty = self.get_specialty(doctor_data)
                    if not specialty:
                        continue

                    # Get profile image
                    profile_image = self.get_profile_image(
                        doctor_data.get("image"), images_dir
                    )

                    # Create or update doctor
                    doctor = self.create_doctor_instance(
                        doctor_data, user, specialty, profile_image
                    )

                    if doctor:
                        # Create schedule and working hours
                        self.create_schedule(doctor)
                        self.create_working_hours(doctor)

                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Created doctor: {doctor_data["name"]}'
                            )
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error creating doctor {doctor_data["name"]}: {str(e)}'
                    )
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} doctors!")
        )

    def create_doctor_user(self, doctor_data):
        """Create user account for doctor"""
        
        email_part = doctor_data['name'].split('.')[1:]
        email_part = ''.join(email_part).strip().replace(" ", "-").lower()
        email = f"{email_part}@hospital.com"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": doctor_data["name"],
                "image": self.get_profile_image(doctor_data.get("image"), settings.BASE_DIR / "doctors/fixtures/doctors/images"),
                "password": make_password("doctor123"),  # Default password
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(f"  → Created user: {email}")

        return user

    def get_specialty(self, doctor_data):
        """Get specialty instance"""
        try:
            return Specialty.objects.get(slug=doctor_data["specialty"])
        except Specialty.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Specialty not found: {doctor_data['specialty']}")
            )
            return None

    def create_doctor_instance(self, doctor_data, user, specialty, profile_image):
        """Create doctor model instance"""
        doctor, created = Doctor.objects.update_or_create(
            user=user,
            defaults={
                "experience": doctor_data["experience"],
                "specialty": specialty,
                "education": doctor_data["degree"],
                "fees": doctor_data["fees"],
                "about": doctor_data["about"],
                "status": Doctor.Status.AVAILABLE,
                "is_verified": True,
                "address_line1": doctor_data["address"]["line1"],
                "address_line2": doctor_data["address"]["line2"],
            },
        )
        return doctor

    def create_schedule(self, doctor):
        """Create default weekly schedule for doctor"""
        # Default schedule: Monday to Friday, 9 AM to 5 PM
        days_schedule = [
            (Days.MON, time(9, 0), time(17, 0)),
            (Days.TUE, time(9, 0), time(17, 0)),
            (Days.WED, time(9, 0), time(17, 0)),
            (Days.THU, time(9, 0), time(17, 0)),
            (Days.FRI, time(9, 0), time(17, 0)),
        ]

        for day, start_time, end_time in days_schedule:
            Schedule.objects.get_or_create(
                doctor=doctor,
                day=day,
                defaults={
                    "start_time": start_time,
                    "end_time": end_time,
                    "max_patients": 5,
                },
            )

    def create_working_hours(self, doctor):
        """Create sample working hours for the next 14 days"""
        today = make_aware(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        )

        for i in range(14):
            day = today + timedelta(days=i)

            # Skip weekends (Saturday=5, Sunday=6)
            if day.weekday() >= 5:
                continue

            # Create working hours from 9 AM to 5 PM
            start_time = make_aware(datetime.combine(day.date(), time(9, 0)))
            end_time = make_aware(datetime.combine(day.date(), time(17, 0)))

            WorkingHours.objects.get_or_create(
                doctor=doctor,
                start_time=start_time,
                end_time=end_time,
                defaults={
                    "patient_left": 5,
                    "status": WorkingHours.Status.UPCOMING,
                },
            )
