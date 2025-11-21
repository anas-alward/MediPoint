from django.db import models
from apps.users.models import User


class Patient(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    def __str__(self):
        return f'{self.user.full_name}'


class PatientFolder(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="folders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.patient} - {self.name}"


class PatientFile(models.Model):
    name = models.CharField(max_length=255, blank=True)
    folder = models.ForeignKey(
        PatientFolder, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to="patients/files/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name or self.file.name
