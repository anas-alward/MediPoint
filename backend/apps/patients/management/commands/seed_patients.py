from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.patients.models import Patient, PatientFolder, PatientFile
import json
from pathlib import Path
from django.contrib.auth import get_user_model


BASE_DIR = Path(__file__).parent.parent.parent / "fixtures" / "seeders" 
PROFILE_FILE_NAME = "profile.json"


User = get_user_model()

class Command(BaseCommand):
    help = "Seed patients with related data"
    

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("This command can only be run in DEBUG mode.")

        profile_data_path= BASE_DIR / PROFILE_FILE_NAME
        
        if not  profile_data_path.exists():
            raise CommandError(f"Profile data file not found at: {profile_data_path}")
        
        with open( profile_data_path, "r") as f:
            patients_data = json.load(f)
        
        print("Seeding patients...")
        user_ids = self.seed_users(patients_data)
        self.seed_patients(user_ids)
        print("Seeding completed.")    
      
    
    def seed_users(self, patients_data):
        ids = []
        for patient_data in patients_data:
            email = patient_data.get("name").replace(" ", ".").lower() + "@example.com"
            
            if user:=User.objects.filter(email=email).first():
                ids.append(user.id)
                print(f"User with email {email} already exists. Skipping.")
                continue

            user = User.objects.create_user(
                email=email,
                password=patient_data.get("password", "patient123"),
                full_name=patient_data.get("name", ""),  
                dob=patient_data.get("dob", None),
                gender=patient_data.get("gender", "M"),
                role=User.Roles.PATIENT,
            )
            ids.append(user.id)
            print(f"Created user: {user.email}")
        return ids
    
    def seed_patients(self, user_ids):
        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            if Patient.objects.filter(user=user).exists():
                print(f"Patient for user {user.email} already exists. Skipping.")
                continue
            
            patient = Patient.objects.create(user=user)
            print(f"Created patient profile for user: {user.email}")
                