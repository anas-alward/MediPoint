from rest_framework import serializers

from apps.doctors.serializers import DoctorSerializer
from apps.patients.serializers import PatientSerializer

from .models import Appointment, Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "appointment",
            "amount",
            "currency",
            "payment_type",
            "status",
            "provider_payment_id",
            "receipt_url",
            "metadata",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "paid_at"]


class AppointmentSerializer(serializers.ModelSerializer):
    datetime = serializers.SerializerMethodField()
    # use source='payment' but allow null=True
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "datetime",
            "doctor",
            "status",
            "fees",
            "working_hours",
            "additional_info",
            "payment",
        ]
        read_only_fields = ["patient", "doctor", "fees"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request", None)

        if request and hasattr(request.user, "is_doctor") and request.user.is_doctor:
            self.fields.pop("doctor", None)
        elif (
            request and hasattr(request.user, "is_patient") and request.user.is_patient
        ):
            self.fields.pop("patient", None)

    def get_datetime(self, obj):
        return obj.working_hours.start_time

    def get_payment(self, obj):
        """
        Returns payment data if exists, otherwise returns default values.
        """
        if hasattr(obj, "payment") and obj.payment:
            return PaymentSerializer(obj.payment, context=self.context).data

        # default dummy payment object if none exists
        return {
            "id": None,
            "appointment": obj.id,
            "amount": obj.fees,
            "currency": "usd",
            "payment_type": "manual",
            "status": "pending",
            "provider_payment_id": None,
            "receipt_url": None,
            "metadata": None,
            "paid_at": None,
            "created_at": None,
            "updated_at": None,
        }

    def to_representation(self, instance):
        request = self.context.get("request")
        representation = super().to_representation(instance)

        context = {"request": request}
        user = request.user if request else None

        if user and hasattr(user, "is_doctor") and user.is_doctor:
            representation["patient"] = PatientSerializer(
                instance.patient, context=context
            ).data
        if user and hasattr(user, "is_patient") and user.is_patient:
            representation["doctor"] = DoctorSerializer(
                instance.doctor, context=context
            ).data

        return representation

    def validate(self, data):
        # Ensure that doctors can only update the status field
        request = self.context.get("request")
        if request and request.method in ["PUT", "PATCH"]:
            user = request.user
            if hasattr(user, "doctor"):
                if "status" not in data or len(data) > 1:
                    raise serializers.ValidationError(
                        "Doctors can only update the status field."
                    )
        return data
