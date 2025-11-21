from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from model_utils.managers import QueryManager

from apps.users.models import User

class Doctor(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "A", "Available"
        UNAVAILABLE = "U", "Unavailable"

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    experience = models.CharField(max_length=50)
    specialty = models.ForeignKey(
        "Specialty",
        on_delete=models.CASCADE,
        related_name="doctors",
        blank=True,
        null=True,
    )
    education = models.CharField(max_length=100)
    fees = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    about = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=50, choices=Status.choices, default=Status.UNAVAILABLE
    )
    is_verified = models.BooleanField(default=False)
    degree_document = models.FileField(
        upload_to="doctor/degree", blank=True, null=True, max_length=1000
    )
    address_line1 = models.CharField(max_length=250, blank=True, default='')
    address_line2 = models.CharField(max_length=250, blank=True, default='')
    
    objects = models.Manager()
    available = QueryManager(status=Status.AVAILABLE)

    def clean(self):
        """Custom validation to ensure a doctor cannot be available without a specialty."""
        if self.status == Doctor.Status.AVAILABLE and not self.specialty:
            raise ValidationError({"specialty": "Doctors cannot be available without a specialty."})

    def save(self, *args, **kwargs):
        """Ensures validation runs before saving the object."""
        self.clean()  # Calls the clean() method before saving
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.full_name

class Specialty(models.Model):
    icon = models.FileField(
        upload_to="specialty/icons",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    class Meta:
        verbose_name = "Specialty"
        verbose_name_plural = "Specialties"

    def __str__(self):
        return self.name


class Days(models.TextChoices):
    SAT = "SAT", "Saturday"
    SUN = "SUN", "Sunday"
    MON = "MON", "Monday"
    TUE = "TUE", "Tuesday"
    WED = "WED", "Wednesday"
    THU = "THU", "Thursday"
    FRI = "FRI", "Friday"


class Schedule(models.Model):
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="schedule"
    )
    day = models.CharField(max_length=50, choices=Days.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_patients = models.IntegerField(default=5)

    def clean(self):
        # Ensure start_time is before end_time
        if self.start_time >= self.end_time:
            raise ValidationError({"start_time": "Start time must be before end time."})

        # Additional validation: Ensure logical consistency with the day
        # (This is more about ensuring proper usage of the model rather than strict validation)

    def save(self, *args, **kwargs):
        # Call the clean method before saving
        self.clean()
        super().save(*args, **kwargs)


class WorkingHoursManager(models.Manager):
    def get_queryset(self):
        # Get the current time
        current_time = now()

        # Filter the queryset to include only upcoming working hours
        return (
            super()
            .get_queryset()
            .filter(
                end_time__gt=current_time,  # end_time should be in the future
            )
        )


class WorkingHours(models.Model):
    class Status(models.TextChoices):
        CANCELED = "C", "Cancelled"
        DONE = "D", "Done"
        UPCOMING = "U", "Upcoming"

    doctor = models.ForeignKey(
        "Doctor", related_name="working_hours", on_delete=models.CASCADE
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    patient_left = models.IntegerField(default=5)
    status = models.CharField(
        max_length=3, choices=Status.choices, default=Status.UPCOMING
    )
    objects = WorkingHoursManager()

    class Meta:
        verbose_name_plural = "Working Hours"

    def clean(self):
        # Ensure start_time is before end_time
        if self.start_time >= self.end_time:
            raise ValidationError({"start_time": "Start time must be before end time."})

    def save(self, *args, **kwargs):
        # Call the clean method before saving
        self.clean()
        super().save(*args, **kwargs)
