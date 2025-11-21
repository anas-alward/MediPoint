from rest_framework import serializers
from .models import Doctor, Specialty, Schedule, WorkingHours
from apps.users.serializers import UserSerializer
from apps.reviews.serializers import ReviewSerializer

class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHours
        fields = ["id", "start_time", "end_time", "doctor", "patient_left"]


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ["id", "start_time", "end_time", "max_patients", "day"]

    def create(self, validated_data):
        # Automatically assign the doctor from the context (logged-in user)
        doctor = self.context['request'].user.doctor
        return Schedule.objects.create(doctor=doctor, **validated_data)

class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ["id", "slug", "name", "icon"]


class DoctorSerializer(serializers.ModelSerializer):
    working_hours = WorkingHoursSerializer(read_only=True, many=True)
    user = UserSerializer(many=False)
    reviews = ReviewSerializer(many=True)
    class Meta:
        model = Doctor
        fields = [
            "user",
            "working_hours",
            "reviews",
            "fees",
            "user",
            "experience",
            "education",
            "specialty",
            "about",
            "address_line1",
            "address_line2",
            "status",
            "is_verified",
            "degree_document",
        ]
        extra_kwargs = {
            "specialty": {"read_only": True},
            "is_verified": {"read_only": True},
            "degree_document": {"write_only": True},
        }

    def __init__(self, *args, **kwargs):
        # Initialize the serializer
        super(DoctorSerializer, self).__init__(*args, **kwargs)

        action = self.context.get("action", None)

        if action == "list":
            self.fields.pop("working_hours", None)

        elif action == "detail":
            self.fields["working_hours"] = WorkingHoursSerializer(
                read_only=True, many=True
            )

    def update(self, instance, validated_data):
        # Handle nested user updates
        user_data = validated_data.pop("user", None)
        
        if user_data:
            user_serializer = UserSerializer(
                instance.user, data=user_data, partial=True
            )
            if user_serializer.is_valid():
                user_serializer.save()
        
        # Update Doctor fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

    def to_representation(self, instance):
        # Call the parent class's to_representation method to get the initial data
        representation = super().to_representation(instance)

        # Check if the request is for a list view
        request = self.context.get("request")
        view = self.context.get("view")
        if request and view and view.action == "list":
            representation.pop("working_hours", None)

        # Customize the 'specialty' field to display the name of the related Specialty model
        if instance.specialty:  # Ensure specialty is not None
            representation["specialty"] = instance.specialty.name
        else:
            representation["specialty"] = (
                None  # Handle the case where specialty is null
            )
        return representation
