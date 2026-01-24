from .models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    is_verified_doctor = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'role', 'email', 'image', 'full_name', 'gender', 'dob', 'is_verified_doctor')
        extra_kwargs = {
            'email': {'read_only':True}
        }

    def get_is_verified_doctor(self, obj):
        if hasattr(obj, 'doctor'):
            return obj.doctor.is_verified
        return False