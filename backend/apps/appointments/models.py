from django.core.exceptions import ValidationError
from django.db import models

from apps.patients.models import Patient
from apps.doctors.models import Doctor, WorkingHours


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PE', 'Pending'
        PAID = 'PA', 'Paid'
        DONE = 'D' , 'Done'
        MISSED = 'M' , 'Missed'
        CANCELLED = 'C' , 'Cancelled'
        DELAYED = 'DE', 'Delayed'
        
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
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    
    
        
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