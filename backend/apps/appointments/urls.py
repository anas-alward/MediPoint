from django.urls import path, include
from rest_framework_nested.routers import SimpleRouter, NestedSimpleRouter
from .views import AppointmentViewSet
from .webhook import stripe_webhook 
from apps.reviews.views import ReviewsViewSet

router = SimpleRouter()

router.register(r"appointments", AppointmentViewSet, basename='appointments')
appointment_router = NestedSimpleRouter(router, r'appointments', lookup='appointment')
appointment_router.register(r"reviews", ReviewsViewSet, basename="appointment-reviews")

appointment_routes = [
    path('', include(router.urls)),
    path('', include(appointment_router.urls)),
    path('webhook/', stripe_webhook, name='appointment_payment_webhook'),
]
