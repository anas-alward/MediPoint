from django.db.models import Q
from rest_framework import permissions
from .models import PatientSharedFolder




class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_patient:
            return True
        
        return False

class IsPatientOwnerOfFolderOrFile(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        
        if request.user.is_doctor:
            doctor = request.user.doctor
            

            allowed_shared_folders = PatientSharedFolder.objects.filter(
                Q(doctor=doctor) | Q(appointment__doctor=doctor)
            ).values_list('folder_id', flat=True)
            print("allowed_shared_folders:", allowed_shared_folders)
            if hasattr(obj, 'folder') and obj.folder.id in allowed_shared_folders:
                return True
        
        # want to check if the obj has either patient attr or folder attr
        if hasattr(obj, 'patient') and obj.patient == request.user.patient:
            return True
        
        
        if hasattr(obj, 'folder') and obj.folder.patient == request.user.patient:
            return True
        
        

        # Write permissions are only allowed to the owner of the patient folder or file
        return False
    