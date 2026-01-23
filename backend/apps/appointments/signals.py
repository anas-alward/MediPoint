from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from apps.users.tasks import send_email_template

@receiver(post_save, sender=Appointment)
def send_new_appointment_email_to_doctor(sender, instance, created, **kwargs):
    """
    Send an email to the doctor when a new appointment is created.
    Optimized to minimize database queries using select_related.
    """
    if not created:
        return

    # Fetch the instance with related fields to avoid multiple queries
    appointment = Appointment.objects.select_related(
        'doctor__user',  # Fetch doctor and their user in one query
        'patient__user',  # Fetch patient and their user in one query
        'working_hours'  # Fetch working hours data
    ).get(id=instance.id)

    send_email_template.delay(
        "New Appointment Booking – Action Required",
        "emails/new_appointment_doctor.html",
        context={
            "doctor_name": appointment.doctor.user.full_name,
            "patient_name": appointment.patient.user.full_name,
            "appointment_data_time": appointment.working_hours.start_time,
            "patient_email": appointment.patient.user.email,
        }, 
        to_email=appointment.doctor.user.email
    )
    
# create new payment record when appointment is created
@receiver(post_save, sender=Appointment)
def create_payment_record_for_appointment(sender, instance, created, **kwargs):
    if created:
        from .models import Payment  # Import here to avoid circular imports

        payment_type = getattr(instance, "_payment_type", Payment.PaymentType.STRIPE)

        if payment_type == Payment.PaymentType.MANUAL:
            payment_type= Payment.PaymentType.MANUAL
        
        if payment_type == Payment.PaymentType.STRIPE:
            payment_type= Payment.PaymentType.STRIPE  
        
        Payment.objects.create(
            appointment=instance,
            amount=instance.fees,
            currency='usd',  # Default currency, adjust as needed
            payment_type=payment_type,  # Use the determined payment type
            status=Payment.Status.PENDING  # Initial status
        )