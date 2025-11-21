from rest_framework import permissions





class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_patient:
            return True
        
        return False

class IsPatientOwnerOfFolderOrFile(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        
        # want to check if the obj has either patient attr or folder attr
        if hasattr(obj, 'patient') and obj.patient == request.user.patient:
            return True
        if hasattr(obj, 'folder') and obj.folder.patient == request.user.patient:
            return True

        # Write permissions are only allowed to the owner of the patient folder or file
        return False
    