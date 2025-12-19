from django.db.models import Sum, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from dateutil.relativedelta import relativedelta
from apps.patients.models import Patient
from django.core.exceptions import ValidationError

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import views
from rest_framework import generics
from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action

from apps.appointments.serializers import AppointmentSerializer
from apps.appointments.models import Appointment
from apps.reviews.models import Review

from .models import Doctor, Schedule, WorkingHours, Specialty
from .permissions import IsOwnerOrReadOnly, IsDoctor
from .filters import DoctorFilter
from .serializers import (
    DoctorSerializer,
    ScheduleSerializer,
    WorkingHoursSerializer,
    SpecialtySerializer,
)


class SpecialtyListAPIView(generics.ListAPIView):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer


class DoctorViewSets(viewsets.ReadOnlyModelViewSet):
    queryset = Doctor.available.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DoctorFilter

    def get_queryset(self):
        queryset = Doctor.available.all()

        if self.action == "list":
            queryset = queryset.select_related("user", "specialty")
        elif self.action == "detail":
            queryset = queryset.select_related("user", "specialty", "working_hours")
        return queryset

    @action(detail=False, methods=["get"])
    def dashboard(self, request, pk=None):
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return Response(
                {"error": "Doctor does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        appointments = Appointment.objects.filter(doctor=doctor).select_related(
            "working_hours"
        )
        total_appointments = appointments.count()
        total_earning = appointments.aggregate(total_earnings=Sum("fees"))[
            "total_earnings"
        ]

        total_patient = appointments.aggregate(
            total_patients=Count("patient", distinct=True)
        )["total_patients"]
        latest_appointment = appointments.order_by("-working_hours__start_time")[:10]

        dashboard_data = {
            "total_earnings": total_earning,
            "total_patients": total_patient,
            "total_appointments": total_appointments,
            "latest_appointments": AppointmentSerializer(
                latest_appointment, context={"request": self.request}, many=True
            ).data,
        }
        return Response(dashboard_data, status=status.HTTP_200_OK)


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    queryset = Schedule.objects.all()
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor
        queryset = Schedule.objects.filter(doctor=doctor)

        return queryset

    def perform_create(self, serializer):
        # Validate the model instance before saving
        try:
            instance = serializer.save()
            instance.full_clean()  # Call full_clean to trigger model-level validation
        except ValidationError as e:
            # Convert Django's ValidationError to DRF's ValidationError
            raise serializers.ValidationError(e.message_dict)

    def perform_update(self, serializer):
        # Validate the model instance before saving
        try:
            instance = serializer.save()
            instance.full_clean()  # Call full_clean to trigger model-level validation
        except ValidationError as e:
            # Convert Django's ValidationError to DRF's ValidationError
            raise serializers.ValidationError(e.message_dict)


class WorkingHoursViewSet(viewsets.ModelViewSet):
    serializer_class = WorkingHoursSerializer

    def get_queryset(self):
        qs = WorkingHours.objects.all()
        doctor_pk = self.kwargs.get("doctor_pk")
        if doctor_pk:
            return qs.filter(doctor_id=doctor_pk)

        return qs


class DoctorInitAPIView(views.APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        doctors = Doctor.objects.select_related("specialty", "user").prefetch_related(
            "reviews", "reviews__comments", "working_hours"
        )
        specialties = Specialty.objects.all()
        # Initialize the response data
        #
        doctors_data = DoctorSerializer(doctors, many=True).data
        specialties_data = SpecialtySerializer(specialties, many=True).data

        response_data = {
            "doctors": doctors_data,
            "specialties": specialties_data,
        }

        return Response(response_data)


# dashboard/views.py


class DashboardDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.today()
        # last three months including current
        months = [(today - relativedelta(months=i)).month for i in range(2, -1, -1)]
        years = [(today - relativedelta(months=i)).year for i in range(2, -1, -1)]

        # Earnings per month (last 3 months)
        earnings_per_month = []
        for m, y in zip(months, years):
            total = (
                Appointment.objects.filter(
                    doctor_id=request.user.id,
                    created_at__year=y,
                    created_at__month=m,
                    status=Appointment.Status.PAID,
                ).aggregate(total=Sum("fees"))["total"]
                or 0
            )
            earnings_per_month.append(total)

        # Trend calculation for earnings
        trend_earnings = 0
        if len(earnings_per_month) >= 2 and earnings_per_month[-2] != 0:
            trend_earnings = (
                (earnings_per_month[-1] - earnings_per_month[-2])
                / earnings_per_month[-2]
            ) * 100

        # Total patients
        total_patients = Patient.objects.count()

        # Total appointments this month
        total_appointments = Appointment.objects.filter(
            created_at__month=today.month, created_at__year=today.year
        ).count()

        # Appointments trend
        appointments_last_month = Appointment.objects.filter(
            created_at__month=(today - relativedelta(months=1)).month,
            created_at__year=(today - relativedelta(months=1)).year,
        ).count()
        trend_appointments = 0
        if appointments_last_month != 0:
            trend_appointments = (
                (total_appointments - appointments_last_month) / appointments_last_month
            ) * 100

        data = {
            "total_earnings": earnings_per_month[-1],
            "earnings_trend": round(trend_earnings, 2),
            "total_patients": total_patients,
            "total_appointments": total_appointments,
            "appointments_trend": round(trend_appointments, 2),
        }
        return Response(data)
