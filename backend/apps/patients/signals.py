from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from .models import PatientFile


@receiver(post_save, sender=PatientFile)
def rename_patient_file(sender, instance, created, **kwargs):
    if created and instance.file:
        old_path = instance.file.path
        extension = os.path.splitext(old_path)[1]
        new_filename = f"{instance.id}{extension}"
        new_path = os.path.join(os.path.dirname(old_path), new_filename)

        os.rename(old_path, new_path)

        # Update model file path
        instance.file.name = os.path.join("patients/files/", new_filename)
        instance.save(update_fields=["file"])
