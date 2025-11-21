from rest_framework import serializers

from apps.doctors.serializers import DoctorSerializer
from apps.patients.serializers import PatientSerializer

from .models import Appointment 

class AppointmentSerializer(serializers.ModelSerializer):
    datetime = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = ['id','patient','datetime', 'doctor', 'status', 'fees', 'working_hours','additional_info']
        read_only_fields = ['patient', 'doctor', 'fees']
    
        def __init__(self, *args, **kwargs):
        # Initialize the serializer
            super(AppointmentSerializer, self).__init__(*args, **kwargs)
            request = self.context.get("request", None)

            if request.user.is_doctor:
                self.fields.pop("doctor", None)
            elif request.user.is_patient:
                self.fields.pop("patient", None)
                

    
    
    def get_datetime(self, obj):
        return obj.working_hours.start_time
    
    def to_representation(self, instance):
        request= self.context['request']
        representation = super().to_representation(instance)
        user = self.context['request'].user

        context={'request': request}
        if user.is_doctor:
            representation['patient'] = PatientSerializer(instance.patient, context=context).data
            
        if user.is_patient:
            representation['doctor'] = DoctorSerializer(instance.doctor, context=context).data

        return representation
    
    def validate(self, data):
        # Ensure that doctors can only update the status field
        if self.context['request'].method in ['PUT', 'PATCH']:
            if hasattr(self.context['request'].user, 'doctor'):
                if 'status' not in data or len(data) > 1:
                    raise serializers.ValidationError(
                        "Doctors can only update the status field."
                    )
        return data