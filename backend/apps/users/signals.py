from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.doctors.models import Doctor
from apps.patients.models import Patient
from .tasks import send_email_template
from .models import User

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Signal to create a Doctor profile if the user's user_type is 'doctor'.
    """
    if created:
        if instance.is_doctor:
            Doctor.objects.create(user=instance)
        
        if instance.is_patient:
            Patient.objects.create(user=instance)



@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        if instance.is_doctor:
            subject = "Welcome to MediPoint – Your Health, Our Priority!"
            template_name = "emails/new_doctor_registration.html"
            context = {
                "doctor_name": instance.full_name,
                "support_email": "support@medipoint.com",
                "support_phone": "+1234567890",
            }
            
        elif instance.is_patient:   
            subject = "Welcome to MediPoint – Your Health, Our Priority!"
            template_name = "emails/new_patient_registration.html"
            context = {
                "patient_name": instance.full_name,
                "support_email": "support@medipoint.com",
                "support_phone": "+1234567890",
            }
            
        send_email_template.delay(subject, template_name, context, instance.email)