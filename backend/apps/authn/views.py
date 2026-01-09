import random

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from rest_framework import serializers
from rest_framework import status, generics, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView

from apps.doctors.serializers import DoctorSerializer
from apps.patients.serializers import PatientSerializer
from apps.users.tasks import send_email_template
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    EmailVerificationSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer




class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        existing_user = User.objects.filter(email=email).first()
        otp_ttl = getattr(settings, "EMAIL_VERIFICATION_OTP_TTL", 15 * 60)

        if existing_user:
            if existing_user.is_email_verified:
                return Response({"message": "User already registered."}, status=status.HTTP_400_BAD_REQUEST)

            otp = f"{random.randint(0, 999999):06d}"
            cache_key = f"email_verification_otp:{email}"
            cache.set(cache_key, otp, timeout=otp_ttl)

            send_email_template.delay(
                "Verify your MediPoint email",
                "emails/verify_email_otp.html",
                {
                    "user_name": existing_user.full_name,
                    "otp": otp,
                    "expiry_minutes": int(otp_ttl / 60),
                    "support_email": "MediPoint@decodaai.com",
                },
                existing_user.email,
            )

            return Response(
                {"message": "Verification OTP resent. Please verify your email."},
                status=status.HTTP_200_OK,
            )

        # Proceed with new registration
        data = request.data.copy()
        data["email"] = email
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(is_email_verified=False)

        otp = f"{random.randint(0, 999999):06d}"
        cache_key = f"email_verification_otp:{email}"
        cache.set(cache_key, otp, timeout=otp_ttl)

        send_email_template.delay(
            "Verify your MediPoint email",
            "emails/verify_email_otp.html",
            {
                "user_name": user.full_name,
                "otp": otp,
                "expiry_minutes": int(otp_ttl / 60),
                "support_email": "MediPoint@decodaai.com",
            },
            user.email,
        )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)



class VerifyEmailView(APIView):
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        cache_key = serializer.validated_data["cache_key"]

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
        cache.delete(cache_key)

        return Response({"message": "Email verified successfully"})



class MeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Dynamically return the appropriate serializer class based on user role."""
        # Get fresh user with relations for serializer determination
        user = (
            User.objects.filter(id=self.request.user.id)
            .select_related("doctor", "patient")
            .first()
        )

        if user.is_doctor:
            return DoctorSerializer
        elif user.is_patient:
            return PatientSerializer
        raise serializers.ValidationError("User role is invalid.")

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_context(self):
        return {"request": self.request, "view": self}

    def get(self, request):
        user = (
            User.objects.filter(id=request.user.id)
            .select_related("doctor", "patient")
            .first()
        )
        if not user:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            serializer_class = self.get_serializer_class()
        except serializers.ValidationError:
            return Response(
                {"detail": "User is neither a doctor nor a patient."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = None
        if user.is_doctor:
            instance = user.doctor
        elif user.is_patient:
            instance = user.patient
        else:
            return Response(
                {"detail": "User profile is incomplete."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def put(self, request):
        user = (
            User.objects.filter(id=request.user.id)
            .select_related("doctor", "patient")
            .first()
        )

        if not request.data:
            return Response(
                {"detail": "No data provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Parse nested data
        parsed_data = request.data.copy()
        if "user" not in parsed_data:
            parsed_data["user"] = {}

        # Handle nested user data in the format user[field_name]
        for key in list(parsed_data.keys()):
            if key.startswith("user["):
                try:
                    field_name = key[5:-1]  # Extract field name from user[field_name]
                    parsed_data["user"][field_name] = parsed_data.pop(key)
                except (IndexError, KeyError):
                    continue

        try:
            serializer_class = self.get_serializer_class()
        except serializers.ValidationError:
            return Response(
                {"detail": "User role is invalid."}, status=status.HTTP_403_FORBIDDEN
            )

        instance = user.doctor if user.is_doctor else user.patient
        if not instance:
            return Response(
                {"detail": "User profile is incomplete."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=parsed_data, partial=True)

        if serializer.is_valid():
            try:
                serializer.save()
                # Return the serialized data of the updated object
                return Response(
                    serializer.data, 
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Invalid data provided.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password updated successfully"}, status=status.HTTP_200_OK)


class PasswordResetRequestView(views.APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        otp_ttl = getattr(settings, "PASSWORD_RESET_OTP_TTL", 600)
        otp = f"{random.randint(0, 999999):06d}"

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Deliberately return the same response to avoid user enumeration
            return Response(
                {"message": "Password reset OTP sent to email."},
                status=status.HTTP_200_OK,
            )

        cache_key = f"password_reset_otp:{email}"
        cache.set(cache_key, otp, timeout=otp_ttl)

        send_email_template.delay(
            "Reset Your MediPoint Password",
            "emails/password_reset.html",
            {
                "user_name": user.full_name,
                "otp": otp,
                "expiry_minutes": int(otp_ttl / 60),
                "support_email": "MediPoint@decodaai.com",
            },
            user.email,
        )
        return Response(
            {"message": "Password reset OTP sent to email."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(views.APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        cache_key = serializer.validated_data["cache_key"]

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        cache.delete(cache_key)

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
