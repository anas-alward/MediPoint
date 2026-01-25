from django.contrib import admin

# Register your models here.


from .models import Patient, PatientSharedFolder, PatientFolder, PatientFile


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Admin View for Patient"""

    list_display = ("user",)
    list_filter = ("user",)


@admin.register(PatientSharedFolder)
class PatientSharedFolderAdmin(admin.ModelAdmin):
    """Admin View for PatientSharedFolder"""

    list_display = ("folder", "sharing_type", "doctor", "appointment")
    list_filter = ("sharing_type", "doctor", "appointment")
