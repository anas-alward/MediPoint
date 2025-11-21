import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.conf import settings
from apps.doctors.models import Specialty


class Command(BaseCommand):
    help = "Seed specialties with icons from JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing specialties before seeding",
        )
        

    def handle(self, *args, **options):
        # Check if the Django settings are in debug mode
        if not settings.DEBUG:
            raise CommandError("This command can only be run in DEBUG mode.")

        json_file_path = settings.BASE_DIR /  "apps/doctors/fixtures/specialties/info.json"
        icons_base_dir = settings.BASE_DIR / "apps/doctors/fixtures/specialties/images"

        try:
            with open(json_file_path, "r") as f:
                specialties_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"Specialties JSON file not found at: {json_file_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in specialties file: {e}")

        if options["clear"]:
            self.clear_specialties()

        self.seed_specialties(specialties_data, icons_base_dir)

    def clear_specialties(self):
        """Clear existing specialties"""
        self.stdout.write("Clearing existing specialties...")
        count, _ = Specialty.objects.all().delete()
        self.stdout.write(f"Deleted {count} specialties")

    def get_icon_file(self, icon_name, icons_base_dir):
        """Get icon file from the icons directory"""
        if not icon_name:
            return None

        # Construct the full path to the icon file
        icon_path = icons_base_dir  / icon_name

        # Check if file exists
        if not os.path.exists(icon_path):
            self.stdout.write(self.style.WARNING(f"Icon file not found: {icon_path}"))
            return None

        try:
            # Open the file and create a Django File object
            with open(icon_path, "rb") as f:
                # Read the file content and create a new File object
                file_content = f.read()

            # Create a new File object with the content
            return File(open(icon_path, "rb"), name=icon_name)

        except IOError as e:
            self.stdout.write(
                self.style.WARNING(f"Could not open icon file: {icon_path} - {e}")
            )
            return None

    def seed_specialties(self, specialties_data, icons_base_dir):
        """Create specialties with icons"""
        self.stdout.write("Seeding specialties...")

        created_count = 0
        updated_count = 0

        for specialty_data in specialties_data:
            try:
                # Get icon file
                icon_file = self.get_icon_file(
                    specialty_data["image"], icons_base_dir
                )

                # Create or update specialty
                specialty, created = Specialty.objects.update_or_create(
                    name=specialty_data["name"],
                    defaults={
                        "slug": specialty_data.get(
                            "slug", specialty_data["slug"]
                        ),
                        "icon": icon_file,
                    },
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Created specialty: {specialty_data["name"]}'
                        )
                    )
                    created_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'↻ Updated specialty: {specialty_data["name"]}'
                        )
                    )
                    updated_count += 1

                # Close the file if it was opened
                if icon_file:
                    try:
                        icon_file.close()
                    except:
                        pass

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error creating specialty {specialty_data["name"]}: {str(e)}'
                    )
                )
                # Ensure file is closed even if there's an error
                if "icon_file" in locals() and icon_file:
                    try:
                        icon_file.close()
                    except:
                        pass
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded specialties! Created: {created_count}, Updated: {updated_count}"
            )
        )