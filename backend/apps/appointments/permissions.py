from rest_framework.permissions import BasePermission
from rest_framework.permissions import SAFE_METHODS

from .models import Payment


class AppointmentPermissions(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True
        
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if request.user.is_patient and obj.patient == request.user.patient:
                return True
            if request.user.is_doctor and obj.doctor == request.user.doctor:
                return True

        return False


class PaymentPermissions(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj: Payment):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return self._is_related_user(request, obj)

        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return self._is_related_user(request, obj)

        return False

    def _is_related_user(self, request, obj: Payment):
        if request.user.is_patient and obj.appointment.patient == request.user.patient:
            return True
        if request.user.is_doctor and obj.appointment.doctor == request.user.doctor:
            return True
        return False