from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from rest_framework import status, generics, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from icecream import ic

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

    def get(self, request):
        user = User.objects.filter(id=request.user.id).select_related("doctor", "patient").first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_doctor:
            return Response(DoctorSerializer(user.doctor, context={"request": request}).data)
        
        if user.is_patient:
            return Response(PatientSerializer(user.patient, context={"request": request}).data)

        return Response(
            {"detail": "User is neither a doctor nor a patient."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def put(self, request):
        # Debugging or logging the incoming data
        ic(self.request.data)
        user = request.user

        # Check if request data is empty
        if not request.data:
            return Response({"detail": "No data provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Parse the incoming data
        parsed_data = {}
        for key in request.data:
            value = request.data.get(key)
            if key.startswith("user"):
                try:
                    # Extract the part inside brackets
                    new_key = key.split("[")[1].rstrip("]")
                    parsed_data.setdefault("user", {})[new_key] = value
                except IndexError:
                    return Response({"detail": f"Malformed key: {key}"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                parsed_data[key] = value

        # Determine the serializer class
        if user.is_doctor:
            serializer_class = DoctorSerializer
        elif user.is_patient:
            serializer_class = PatientSerializer
        else:
            return Response({"detail": "User role is invalid."}, status=status.HTTP_403_FORBIDDEN)

        # Access the related model instance
        model_instance = user.doctor if user.is_doctor else user.patient if user.is_patient else None
        if not model_instance:
            return Response({"detail": "User profile is incomplete."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate and save the data
        serializer = serializer_class(model_instance, data=parsed_data, partial=True)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(
                    {"message": f"{'Doctor' if user.is_doctor else 'Patient'} profile updated successfully"},
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                # Handle the specific ValueError raised by the Doctor model's save method
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Handle validation errors
        return Response({
            "detail": "Invalid data provided.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


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
