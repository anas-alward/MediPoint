import stripe

from django.conf import settings
from django.core.exceptions import ValidationError

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets


from apps.users.tasks import send_email_template

from .serializers import AppointmentSerializer
from .permissions import AppointmentPermissions
from .models import Appointment, WorkingHours


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentPermissions]

    def get_serializer(self, *args, **kwargs):
        # Pass the request context to the serializer
        kwargs["context"] = {"request": self.request}
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.is_patient:
            return Appointment.objects.filter(patient=user.patient).select_related("doctor").order_by('-created_at')
        elif user.is_doctor:
            return Appointment.objects.filter(doctor=user.doctor).select_related("patient").order_by('-created_at')
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
                    "patient_name":appointment.patient.user.full_name,
                    "doctor_name":appointment.doctor.user.full_name,
                    "support_email":"MediPoint@decodaai.com",
                    "support_phone":"+123456789"
                },
                to_email=appointment.patient.user.email
            )
        elif request.user.is_patient:
            send_email_template.delay(
                "Appointment Cancellation by Patient",
                "emails/appointment_cancelled_doctor.html",
                context={
                    "patient_name":appointment.patient.user.full_name,
                    "doctor_name":appointment.doctor.user.full_name,
                    "appointment_date_time":appointment.working_hours.start_time
                },
                to_email=appointment.doctor.user.email
            )

        return Response({"message": "Appointment canceled"}, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"], permission_classes=[AppointmentPermissions])
    def pay(self, request, pk=None):
        """Creates a Stripe Checkout session for this appointment."""
        appointment = self.get_object()

        if not request.user.is_patient or appointment.patient != request.user.patient:
            return Response(
                {"detail": "Only the patient can make a payment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Appointment with Dr. {appointment.doctor.user.full_name}",
                            },
                            "unit_amount": int(
                                appointment.fees * 100
                            ),  # Convert to cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url="https://medipoint.decodaai.com/p/my-appointments",  # Replace with your frontend URL
                cancel_url="https://medipoint.decodaai.com/p/my-appointments",
                metadata={"appointment_id": appointment.id},
            )

            return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[AppointmentPermissions])
    def complete(self, request, pk=None):
        appointment = self.get_object()

        try:
            appointment.complete()
            return Response({"status": "Appointment completed successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    