from django.urls import path

from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    RegisterView,
    MeView,
    CustomTokenObtainPairView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    PasswordResetConfirmView,
    VerifyEmailView,
    ResendEmailVerificationView,
    DoctorMeView,
    PatientMeView,
)

urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("password/change/", PasswordChangeView.as_view(), name="change_password"),
    path(
        "password/reset/",
        PasswordResetRequestView.as_view(),
        name="reset_password_request",
    ),
    path(
        "password/reset/verify/",
        PasswordResetVerifyView.as_view(),
        name="reset_password_verify",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetVerifyView.as_view(),
        name="reset_password_confirm",
    ),
    path("me/doctor/", DoctorMeView.as_view(), name="doctor_me"),
    path("me/patient/", PatientMeView.as_view(), name="patient_me"),
    path("me/", MeView.as_view()),
    path("register/", RegisterView.as_view()),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path(
        "verify-email/resend/",
        ResendEmailVerificationView.as_view(),
        name="resend_verify_email",
    ),
]
