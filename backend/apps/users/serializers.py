from .models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'role', 'email', 'image', 'full_name', 'gender', 'dob', )
        extra_kwargs = {
            'email': {'read_only':True}
        }

