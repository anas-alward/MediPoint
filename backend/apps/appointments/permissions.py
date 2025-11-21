from rest_framework.permissions import BasePermission

class AppointmentPermissions(BasePermission):
    def has_permission(self, request, view):
        # Allow authenticated users to create appointments
        if request.user.is_authenticated:
            return True
        
        return False

    def has_object_permission(self, request, view, obj):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return False

        # Allow patients to update or delete their own appointments
        if request.method in [ 'POST', 'PUT', 'PATCH', 'DELETE']:
            if request.user.is_patient and obj.patient == request.user.patient:
                return True
            
            if request.user.is_doctor and obj.doctor == request.user.doctor:
                return True
            
        return False