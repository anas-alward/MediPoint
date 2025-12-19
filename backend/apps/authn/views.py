from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from rest_framework import status, generics, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from icecream import ic
from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings

from .tokens import email_verification_token


from apps.doctors.serializers import DoctorSerializer
from apps.patients.serializers import PatientSerializer
from apps.users.tasks import send_email_template
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from rest_framework.views import APIView
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
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

    def perform_create(self, serializer):
        user = serializer.save(is_email_verified=False)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)

        verify_url = f"{settings.FRONTEND_URL}/verify-email/?uid={uid}&token={token}"

        send_mail(
            subject="Verify your email",
            message=f"Click the link to verify your email: {verify_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return user



class VerifyEmailView(APIView):
    def get(self, request):
        uid = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uid or not token:
            return Response({"error": "Invalid link"}, status=400)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except Exception:
            return Response({"error": "Invalid user"}, status=400)

        if email_verification_token.check_token(user, token):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
            return Response({"message": "Email verified successfully"})
        else:
            return Response({"error": "Invalid or expired token"}, status=400)



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

        instance = user.doctor if user.is_doctor else user.patient
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
                return Response(
                    {
                        "message": f"{'Doctor' if user.is_doctor else 'Patient'} profile updated successfully"
                    },
                    status=status.HTTP_200_OK,
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
        
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "Password reset link sent to email."}, status=status.HTTP_200_OK)

        domain = request.data.get('domain')
        if not domain:
            return Response({"message": "Request must contain domain."}, status=status.HTTP_400_BAD_REQUEST)
        
        reset_link = f"{domain}/password-reset/{urlsafe_base64_encode(force_bytes(user.pk))}/{default_token_generator.make_token(user)}/"
        send_email_template.delay(
            "Reset Your MediPoint Password",
            "emails/password_reset.html",
            {"user_name": user.full_name, "reset_link": reset_link, "support_email": "MediPoint@decodaai.com"},
            user.email,
        )
        return Response({"message": "Password reset link sent to email."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(views.APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
