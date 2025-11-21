from django.db import models
from apps.appointments.models import Appointment
from apps.core.models import AuditableModel
from apps.patients.models import Patient
from django.contrib.auth import get_user_model
User = get_user_model()

class Review(AuditableModel):
    class RatingChoices(models.IntegerChoices):
        ONE = 1, "1 Star"
        TWO = 2, "2 Stars"
        THREE = 3, "3 Stars"
        FOUR = 4, "4 Stars"
        FIVE = 5, "5 Stars"
    
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="review")
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(choices=RatingChoices.choices, default=RatingChoices.FIVE)
    content = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Review by {self.patient.username} for {self.doctor.user.get_full_name()}"

    class Meta:
        unique_together = ('appointment', 'patient')


class Comment(AuditableModel):
    

    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name="comments"
    )   
    type = models.CharField(max_length=50, choices=[('D', 'Doctor'), ('P', 'Patient')])
    user = models.ForeignKey(User , on_delete=models.CASCADE)
    content = models.TextField()
    
    
    def __str__(self):
        return f"Comment by {self.user.get_full_name()} on Review {self.review.id}"
    
    