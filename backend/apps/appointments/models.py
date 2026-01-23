from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.patients.models import Patient
from apps.doctors.models import Doctor, WorkingHours


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PE', 'Pending'
        PAID = 'PA', 'Paid'
        DONE = 'D' , 'Done'
        MISSED = 'M' , 'Missed'
        CANCELLED = 'C' , 'Cancelled'
        # DELAYED = 'DE', 'Delayed'
        # PAYMENT_FAILED = 'PF', 'Payment Failed'
        
    patient = models.ForeignKey(
        Patient,
        related_name='appointments',
        on_delete=models.CASCADE
    )
    status = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=50)
    doctor = models.ForeignKey(
        Doctor, 
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    working_hours = models.ForeignKey(
        WorkingHours,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    fees = models.DecimalField(max_digits=5, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    additional_info = models.TextField(blank=True, null=True)
    # payment_id = models.CharField(max_length=100, blank=True, null=True)
    
    
        
    def __str__(self):
        return f'{self.patient} - {self.doctor}'
    
    def cancel(self):
        if(self.status != Appointment.Status.PENDING):
            raise ValidationError('Appointment can be cancelled only when they are pending')
        self.status = Appointment.Status.CANCELLED
        self.working_hours.patient_left += 1
        
        self.save()
        
    def complete(self):
        if self.status == Appointment.Status.DONE or self.status == Appointment.Status.CANCELLED:
            raise ValidationError('Appointment that are done or cancelled or complete cannot be complete')
        
        self.status = Appointment.Status.DONE
        self.save()


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        REFUNDED = "refunded", "Refunded"

    appointment = models.OneToOneField(
        "Appointment",
        related_name="payment",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10, default="usd")
    payment_type = models.CharField(
        max_length=20, choices=PaymentType.choices, default=PaymentType.STRIPE
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    provider_payment_id = models.CharField(max_length=255, blank=True, null=True)
    receipt_url = models.URLField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for appointment {self.appointment_id} ({self.payment_type})"

    def mark_succeeded(self, provider_payment_id: str | None = None, receipt_url: str | None = None, metadata=None):
        self.status = Payment.Status.SUCCEEDED
        self.paid_at = self.paid_at or timezone.now()
        if provider_payment_id:
            self.provider_payment_id = provider_payment_id
        if receipt_url:
            self.receipt_url = receipt_url
        if metadata is not None:
            self.metadata = metadata
        self.save(update_fields=[
            "status",
            "paid_at",
            "provider_payment_id",
            "receipt_url",
            "metadata",
            "updated_at",
        ])

    def mark_failed(self, provider_payment_id: str | None = None, metadata=None):
        self.status = Payment.Status.FAILED
        if provider_payment_id:
            self.provider_payment_id = provider_payment_id
        if metadata is not None:
            self.metadata = metadata
        self.save(update_fields=[
            "status",
            "provider_payment_id",
            "metadata",
            "updated_at",
        ])