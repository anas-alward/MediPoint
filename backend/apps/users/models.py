from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Genders(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"

    class Roles(models.TextChoices):
        DOCTOR = "D", "Doctor"
        PATIENT = "P", "Patient"
        ADMIN = "A", "ADMIN"

    username = None
    id = models.UUIDField(
        unique=True, editable=False, primary_key=True, default=uuid.uuid4
    )
    image = models.ImageField(upload_to="users/profile/", null=True, blank=True)
    role = models.CharField(max_length=50, choices=Roles.choices, default=Roles.PATIENT)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    gender = models.CharField(
        max_length=10, choices=Genders.choices, default=Genders.MALE
    )
    dob = models.DateField(blank=True, null=True)
    objects = UserManager()
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False) ## just added this
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.email

    @property
    def is_doctor(self):
        return self.role == User.Roles.DOCTOR

    @property
    def is_admin(self):
        return self.role == User.Roles.ADMIN

    @property
    def is_patient(self):
        return self.role == User.Roles.PATIENT
