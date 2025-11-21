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
    PasswordResetConfirmView,
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
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="reset_password_confirm",
    ),
    path("me/", MeView.as_view()),
    path("register/", RegisterView.as_view()),
]
