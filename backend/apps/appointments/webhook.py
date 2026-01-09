import stripe

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apps.users.tasks import send_email_template
from .models import Appointment, Payment


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
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

    # --- Handle PaymentIntent events ---
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        appointment_id = intent.get("metadata", {}).get("appointment_id")

        if appointment_id:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            payment, _ = Payment.objects.get_or_create(
                appointment=appointment,
                defaults={
                    "amount": appointment.fees,
                    "currency": intent.get("currency", "usd"),
                    "payment_type": Payment.PaymentType.STRIPE,
                    "provider_payment_id": intent.get("id"),
                    "metadata": intent.get("metadata"),
                },
            )

            charges = intent.get("charges", {}).get("data", [])
            receipt_url = None
            if charges and isinstance(charges, list):
                receipt_url = charges[0].get("receipt_url")

            payment.payment_type = Payment.PaymentType.STRIPE
            payment.amount = appointment.fees
            payment.currency = intent.get("currency", "usd")
            payment.save(update_fields=["payment_type", "amount", "currency", "updated_at"])

            payment.mark_succeeded(
                provider_payment_id=intent.get("id"),
                receipt_url=receipt_url,
                metadata=intent.get("metadata"),
            )

            appointment.status = Appointment.Status.PAID
            appointment.payment_id = intent["id"]  # Store PaymentIntent ID
            appointment.save(update_fields=["status", "payment_id"])

            send_email_template.delay(
                "Payment Notification to Doctor",
                "emails/payment_notification_doctor.html",
                context={
                    "doctor_name": appointment.doctor.user.full_name,
                    "patient_name": appointment.patient.user.full_name,
                    "appointment_date_time": appointment.working_hours.start_time,
                    "payment_amount": appointment.fees,
                    "payment_method": "Online"
                },
                to_email=appointment.doctor.user.email
            )

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        appointment_id = intent.get("metadata", {}).get("appointment_id")
        if appointment_id:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            payment, _ = Payment.objects.get_or_create(
                appointment=appointment,
                defaults={
                    "amount": appointment.fees,
                    "currency": intent.get("currency", "usd"),
                    "payment_type": Payment.PaymentType.STRIPE,
                    "provider_payment_id": intent.get("id"),
                    "metadata": intent.get("metadata"),
                },
            )

            payment.payment_type = Payment.PaymentType.STRIPE
            payment.amount = appointment.fees
            payment.currency = intent.get("currency", "usd")
            payment.save(update_fields=["payment_type", "amount", "currency", "updated_at"])
            payment.mark_failed(provider_payment_id=intent.get("id"), metadata=intent.get("metadata"))

            appointment.status = Appointment.Status.PAYMENT_FAILED
            appointment.save(update_fields=["status"])

    return JsonResponse({"status": "success"}, status=200)
