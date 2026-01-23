import stripe

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from .paginations import AppointmentPagination
from apps.users.tasks import send_email_template

from .serializers import (
    AppointmentSerializer,
    ManualAppointmentCreateSerializer,
    PaymentSerializer,
)
from .permissions import AppointmentPermissions, PaymentPermissions
from .models import Appointment, WorkingHours, Payment
from apps.users.pagination import CustomPageNumberPagination
from apps.users.models import User
from apps.patients.models import Patient


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentPermissions]
    pagination_class = CustomPageNumberPagination

    def get_serializer(self, *args, **kwargs):
        # Pass the request context to the serializer
        kwargs["context"] = {"request": self.request}
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.is_patient:
            return (
                Appointment.objects.filter(patient=user.patient)
                .select_related("doctor")
                .order_by("-created_at")
            )
        elif user.is_doctor:
            return (
                Appointment.objects.filter(doctor=user.doctor)
                .select_related("patient")
                .order_by("-created_at")
            )
        return Appointment.objects.none()

    def perform_create(self, serializer):
        if not self.request.user.is_patient:
            raise ValidationError("Only patients can create appointments.")

        working_hour_id = self.request.data.get("working_hours")
        try:
            working_hours = WorkingHours.objects.get(id=working_hour_id)
            if not working_hours.patient_left:
                raise ValidationError("This working hours is at capacity.")

        except WorkingHours.DoesNotExist:
            raise ValidationError("Invalid doctor ID.")

        fees = working_hours.doctor.fees
        doctor = working_hours.doctor

        serializer.save(patient=self.request.user.patient, doctor=doctor, fees=fees)
        print("Appointment created:", serializer.data.get("id"))

    # Patient can cancel appointments they made
    # Doctor can cancel appointments they have
    @action(detail=True, methods=["post"], permission_classes=[AppointmentPermissions])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        try:
            appointment.cancel()

        except Exception as e:
            return Response(
                {"message": f"{str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.is_doctor:
            send_email_template.delay(
                "Appointment Cancellation by Doctor",
                "emails/appointment_cancelled_patient.html",
                context={
                    "patient_name": appointment.patient.user.full_name,
                    "doctor_name": appointment.doctor.user.full_name,
                    "support_email": "MediPoint@decodaai.com",
                    "support_phone": "+123456789",
                },
                to_email=appointment.patient.user.email,
            )
        elif request.user.is_patient:
            send_email_template.delay(
                "Appointment Cancellation by Patient",
                "emails/appointment_cancelled_doctor.html",
                context={
                    "patient_name": appointment.patient.user.full_name,
                    "doctor_name": appointment.doctor.user.full_name,
                    "appointment_date_time": appointment.working_hours.start_time,
                },
                to_email=appointment.doctor.user.email,
            )

        return Response({"message": "Appointment canceled"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="manual-create-by-doctor")
    def manual_create_by_doctor(self, request):
        """Allow doctors to manually create an appointment for a patient by email/name."""

        if not request.user.is_doctor:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = ManualAppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        working_hours = data["working_hours"]

        # Doctor can only book their own working hours
        if working_hours.doctor != request.user.doctor:
            return Response(
                {"detail": "You can only create appointments for your own slots."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Resolve or create user/patient
        user = User.objects.filter(email__iexact=data["email"]).first()
        patient_created = False

        if user:
            if not hasattr(user, "patient"):
                patient = Patient.objects.create(user=user)
            else:
                patient = user.patient
        else:
            user = User.objects.create_user(
                email=data["email"],
                password=None,
                full_name=data["full_name"],
                role=User.Roles.PATIENT,
            )
            user.set_unusable_password()
            user.save(update_fields=["password", "role", "full_name", "email"])
            patient = Patient.objects.create(user=user)
            patient_created = True

        appointment = Appointment(
            patient=patient,
            doctor=request.user.doctor,
            working_hours=working_hours,
            fees=working_hours.doctor.fees,
        )
        appointment._payment_type = Payment.PaymentType.MANUAL
        appointment.save()


        response_data = AppointmentSerializer(
            appointment, context={"request": request}
        ).data
        response_data.update({"patient_created": patient_created})

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="create-payment-intent")
    def create_payment_intent(self, request, pk=None):
        appointment = self.get_object()

        if appointment.patient != request.user.patient:
            return Response(status=403)

        stripe.api_key = settings.STRIPE_SECRET_KEY

        payment, _ = Payment.objects.get_or_create(
            appointment=appointment,
            defaults={
                "amount": appointment.fees,
                "currency": "usd",
                "payment_type": Payment.PaymentType.STRIPE,
            },
        )

        if payment.payment_type != Payment.PaymentType.STRIPE:
            return Response(
                {"message": "This appointment is configured for manual payments."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.status = Payment.Status.PENDING
        payment.amount = appointment.fees
        payment.currency = "usd"
        payment.save(update_fields=["status", "amount", "currency", "updated_at"])

        intent = stripe.PaymentIntent.create(
            amount=int(appointment.fees * 100),
            currency="usd",
            automatic_payment_methods={"enabled": True},
            metadata={
                "appointment_id": appointment.id,
                "user_id": request.user.id,
            },
        )

        payment.provider_payment_id = intent.id
        payment.metadata = dict(intent.metadata)
        payment.save(update_fields=["provider_payment_id", "metadata", "updated_at"])

        return Response({"client_secret": intent.client_secret}, status=200)

    @action(
        detail=True,
        methods=["post"],
        url_path="manual-payment",
        permission_classes=[AppointmentPermissions],
    )
    def manual_payment(self, request, pk=None):
        appointment = self.get_object()

        # Ensure the caller is either the patient or doctor tied to this appointment
        user = request.user
        if user.is_patient and appointment.patient != user.patient:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if user.is_doctor and appointment.doctor != user.doctor:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if hasattr(appointment, "payment"):
            return Response(
                {"message": "Payment already exists for this appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = request.data.get("amount") or appointment.fees
        currency = request.data.get("currency") or "usd"
        status_value = request.data.get("status") or Payment.Status.SUCCEEDED
        reference = request.data.get("reference")
        metadata = request.data.get("metadata")

        payment = Payment.objects.create(
            appointment=appointment,
            amount=amount,
            currency=currency,
            payment_type=Payment.PaymentType.MANUAL,
            status=status_value,
            provider_payment_id=reference,
            metadata=metadata,
            paid_at=timezone.now()
            if status_value == Payment.Status.SUCCEEDED
            else None,
        )

        if payment.status == Payment.Status.SUCCEEDED:
            appointment.status = Appointment.Status.PAID
            appointment.payment_id = payment.provider_payment_id
            appointment.save(update_fields=["status", "payment_id"])
        elif payment.status == Payment.Status.FAILED:
            appointment.status = Appointment.Status.PAYMENT_FAILED
            appointment.save(update_fields=["status"])

        serializer = PaymentSerializer(payment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[AppointmentPermissions])
    def complete(self, request, pk=None):
        appointment = self.get_object()

        try:
            appointment.complete()
            return Response(
                {"status": "Appointment completed successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [PaymentPermissions]

    def get_queryset(self):
        user = self.request.user
        base_qs = Payment.objects.select_related(
            "appointment",
            "appointment__patient",
            "appointment__doctor",
        )

        if user.is_patient:
            return base_qs.filter(appointment__patient=user.patient)
        if user.is_doctor:
            return base_qs.filter(appointment__doctor=user.doctor)
        return Payment.objects.none()

    def perform_create(self, serializer):
        appointment = serializer.validated_data.get("appointment")
        if appointment is None:
            raise ValidationError("Appointment is required to create a payment.")

        user = self.request.user
        if user.is_patient and appointment.patient != user.patient:
            raise ValidationError("You cannot create payments for other patients.")
        if user.is_doctor and appointment.doctor != user.doctor:
            raise ValidationError("You cannot create payments for other doctors.")

        if hasattr(appointment, "payment"):
            raise ValidationError("A payment already exists for this appointment.")

        status_value = serializer.validated_data.get("status", Payment.Status.PENDING)
        paid_at = serializer.validated_data.get("paid_at")
        if status_value == Payment.Status.SUCCEEDED and paid_at is None:
            paid_at = timezone.now()

        payment = serializer.save(
            amount=serializer.validated_data.get("amount", appointment.fees),
            currency=serializer.validated_data.get("currency", "usd"),
            paid_at=paid_at,
        )

        if payment.status == Payment.Status.SUCCEEDED:
            appointment.status = Appointment.Status.PAID
            appointment.payment_id = (
                payment.provider_payment_id or appointment.payment_id
            )
            appointment.save(update_fields=["status", "payment_id"])

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        payment = serializer.save()

        if payment.status == Payment.Status.SUCCEEDED and payment.paid_at is None:
            payment.paid_at = timezone.now()
            payment.save(update_fields=["paid_at", "updated_at"])

        if payment.status != previous_status:
            appointment = payment.appointment
            if payment.status == Payment.Status.SUCCEEDED:
                appointment.status = Appointment.Status.PAID
                appointment.payment_id = (
                    payment.provider_payment_id or appointment.payment_id
                )
                appointment.save(update_fields=["status", "payment_id"])
            elif payment.status == Payment.Status.FAILED:
                appointment.status = Appointment.Status.PAYMENT_FAILED
                appointment.save(update_fields=["status"])
            elif payment.status == Payment.Status.CANCELED:
                appointment.status = Appointment.Status.CANCELLED
                appointment.payment_id = None
                appointment.save(update_fields=["status", "payment_id"])

    def perform_destroy(self, instance):
        appointment = instance.appointment
        super().perform_destroy(instance)
        if appointment.status == Appointment.Status.PAID:
            appointment.status = Appointment.Status.PENDING
        appointment.payment_id = None
        appointment.save(update_fields=["status", "payment_id"])
