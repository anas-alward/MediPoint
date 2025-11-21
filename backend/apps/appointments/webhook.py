import stripe

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apps.users.tasks import send_email_template

from .models import Appointment



stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Allows access without authentication
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # Handle event types
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Extract metadata (assuming you store appointment ID in metadata)
        appointment_id = session.get("metadata", {}).get("appointment_id")
        if appointment_id:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            appointment.status = Appointment.Status.PAID
            appointment.payment_id = session["payment_intent"]
            appointment.save()
            send_email_template.delay(
                "Payment Notification to Doctor",
                "emails/payment_notification_doctor.html",
                context={
                    'doctor_name':appointment.doctor.user.full_name,
                    'patient_name':appointment.patient.user.full_name,
                    'appointment_date_time':appointment.working_hours.start_time,
                    'payment_amount': appointment.fees,
                    'payment_method': "Online"
                },
                to_email=appointment.doctor.user.email
            )
            
    return JsonResponse({"status": "success"}, status=200)
