from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import views
from rest_framework import generics
from rest_framework import viewsets
from rest_framework import serializers

from rest_framework import status
from rest_framework.decorators import action
from dateutil.relativedelta import relativedelta
from datetime import datetime

from apps.appointments.serializers import AppointmentSerializer
from apps.appointments.models import Appointment
from apps.users.models import User

from .models import Doctor, Schedule, WorkingHours, Specialty, PatientReport
from .permissions import IsOwnerOrReadOnly, IsDoctor
from .filters import DoctorFilter
from .serializers import (
    DegreeDocumentUploadSerializer,
    DoctorSerializer,
    ScheduleSerializer,
    WorkingHoursSerializer,
    SpecialtySerializer,
    PatientReportSerializer,
)
from apps.users.tasks import send_email_template


from datetime import timedelta


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

        three_months_ago = timezone.now() - timedelta(days=90)
        appointments = Appointment.objects.filter(
            doctor=doctor,
            working_hours__start_time__gte=three_months_ago,
        ).select_related("working_hours", "patient__user")

        gender_breakdown = (
            appointments.values(
                "working_hours",
                "working_hours__start_time",
                "working_hours__end_time",
            )
            .annotate(
                female_patients=Count(
                    "id",
                    filter=Q(patient__user__gender=User.Genders.FEMALE),
                ),
                male_patients=Count(
                    "id",
                    filter=Q(patient__user__gender=User.Genders.MALE),
                ),
            )
            .order_by("working_hours__start_time")
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
            "appointments_by_working_hours": list(gender_breakdown),
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

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])

        if not ids:
            return Response(
                {"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # We use self.get_queryset() to ensure the doctor
        # can only delete THEIR own schedules.
        queryset = self.get_queryset().filter(id__in=ids)

        deleted_count, _ = queryset.delete()

        return Response(
            {"message": f"Successfully deleted {deleted_count} schedules."},
            status=status.HTTP_204_NO_CONTENT,
        )


class WorkingHoursViewSet(viewsets.ModelViewSet):
    serializer_class = WorkingHoursSerializer

    def get_queryset(self):
        qs = WorkingHours.objects.all()
        doctor_pk = self.kwargs.get("doctor_pk")
        if doctor_pk:
            return qs.filter(doctor_id=doctor_pk)

        return qs

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])

        if not ids:
            return Response(
                {"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # We use self.get_queryset() to ensure the doctor
        # can only delete THEIR own schedules.
        queryset = self.get_queryset().filter(id__in=ids)

        deleted_count, _ = queryset.delete()

        return Response(
            {"message": f"Successfully deleted {deleted_count} schedules."},
            status=status.HTTP_204_NO_CONTENT,
        )


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


class DashboardDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        start_current_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        start_next_month = start_current_month + relativedelta(months=1)
        start_three_months_ago = start_current_month - relativedelta(months=3)

        paid_appointments = Appointment.objects.filter(
            doctor__user=request.user,
            created_at__gte=start_three_months_ago,
            created_at__lt=start_next_month,
        )

        earnings_this_month = (
            paid_appointments.aggregate(total=Sum("fees"))["total"] or 0
        )

        # ---------------------------------------------
        # 1. Build ALL dates with zero values
        # ---------------------------------------------
        date_cursor = start_three_months_ago.date()
        end_date = start_next_month.date()

        summary = {}
        while date_cursor < end_date:
            date_str = date_cursor.isoformat()
            summary[date_str] = {"M": set(), "F": set()}
            date_cursor += timedelta(days=1)

        # ---------------------------------------------
        # 2. Fill real data (unique patients)
        # ---------------------------------------------
        patients_data = paid_appointments.values_list(
            "patient__user__id",
            "patient__user__gender",
            "created_at",
        )

        unique_patients = set()

        for patient_id, gender, created_at in patients_data:
            date_str = created_at.date().isoformat()
            summary[date_str][gender].add(patient_id)
            unique_patients.add(patient_id)

        # ---------------------------------------------
        # 3. Serialize for response
        # ---------------------------------------------
        patients_summary = [
            {
                "date": date,
                "M": len(counts["M"]),
                "F": len(counts["F"]),
            }
            for date, counts in sorted(summary.items())
        ]

        data = {
            "total_earnings": earnings_this_month,
            "total_patients": len(unique_patients),  # UNIQUE patients
            "patients_summary": patients_summary,  # FULL timeline
            "total_appointments": paid_appointments.count(),
        }

        return Response(data)


class PatientReportViewSet(viewsets.ModelViewSet):
    serializer_class = PatientReportSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        return PatientReport.objects.filter(doctor=self.request.user.doctor)

    def perform_create(self, serializer):
        serializer.save()


class DegreeDocumentUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request):
        doctor = getattr(request.user, "doctor", None)
        if not doctor:
            return Response(
                {"detail": "User is not a doctor."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DegreeDocumentUploadSerializer(
            doctor, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save(is_verified=False)

            admin_email = (
                getattr(settings, "ADMIN_REVIEW_EMAIL", None)
                or getattr(settings, "SERVER_EMAIL", None)
                or getattr(settings, "DEFAULT_FROM_EMAIL", None)
            )

            if admin_email:
                send_email_template.delay(
                    subject="New doctor degree document submitted",
                    template_name="emails/doctor_degree_uploaded.html",
                    context={
                        "doctor_name": doctor.user.full_name,
                        "doctor_email": doctor.user.email,
                        "submitted_at": timezone.now(),
                    },
                    to_email=admin_email,
                )

            return Response(
                {"detail": "Degree document submitted. We will review it soon."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Invalid data provided.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
