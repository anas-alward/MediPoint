from rest_framework.permissions import BasePermission

class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        # Write permissions are only allowed to the owner of the doctor profile
        return obj.user == request.user
    
class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_doctor:
            return True
        
        return False 