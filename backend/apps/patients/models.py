from django.core.exceptions import ValidationError
from django.db import models
from apps.users.models import User


class Patient(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    def __str__(self):
        return f"{self.user.full_name}"

    @property
    def protected_relative_path(self):
        return self.file.name  

class PatientFolder(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="folders"
    )
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


class PatientSharedFolder(models.Model):
    class SharingType(models.TextChoices):
        DOCTOR = "DOCTOR", "Doctor"
        APPOINTMENT = "APPOINTMENT", "Appointment"

    folder = models.ForeignKey(
        PatientFolder,
        on_delete=models.CASCADE,
        related_name="shared_entries",
    )
    sharing_type = models.CharField(max_length=20, choices=SharingType.choices)
    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="shared_folders",
        blank=True,
        null=True,
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name="shared_folders",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Ensure sharing target matches the sharing type and is consistent with the folder's patient
        if self.sharing_type == self.SharingType.DOCTOR:
            if not self.doctor:
                raise ValidationError(
                    {"doctor": "Doctor is required for doctor sharing."}
                )
            if self.appointment:
                raise ValidationError(
                    {"appointment": "Appointment must be empty for doctor sharing."}
                )
        elif self.sharing_type == self.SharingType.APPOINTMENT:
            if not self.appointment:
                raise ValidationError(
                    {"appointment": "Appointment is required for appointment sharing."}
                )
            if self.doctor:
                raise ValidationError(
                    {"doctor": "Doctor must be empty for appointment sharing."}
                )
            if (
                self.folder
                and self.appointment
                and self.folder.patient_id != self.appointment.patient_id
            ):
                raise ValidationError(
                    {
                        "appointment": "Appointment must belong to the same patient as the folder."
                    }
                )
        else:
            raise ValidationError({"sharing_type": "Invalid sharing type."})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        target = self.doctor or self.appointment
        return f"{self.folder} -> {target} ({self.sharing_type})"
