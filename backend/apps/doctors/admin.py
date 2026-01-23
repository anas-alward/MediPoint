from django.contrib import admin
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html

from apps.users.tasks import send_email_template
from .models import Doctor, Specialty, Schedule, WorkingHours, PatientReport
from .forms import ScheduleTabularInlineModelForm


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


class ScheduleInline(admin.TabularInline):
    """Tabular Inline View for Schedule"""

    model = Schedule
    form = ScheduleTabularInlineModelForm
    min_num = 0
    max_num = 10
    extra = 0


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ["start_time", "end_time", "day", "doctor"]


@admin.register(PatientReport)
class PatientReportAdmin(admin.ModelAdmin):
    list_display = ["doctor", "patient", "reason", "created_at"]
    list_filter = ["doctor__user__full_name", "created_at"]
    search_fields = ["doctor__user__full_name", "patient__user__full_name", "reason"]


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ['start_time', 'end_time','doctor', 'id']
    list_filter = ['doctor__user__full_name', 'id']
    search_fields = ['id']





@admin.action(description="Verify selected doctors")
def verify_doctors(modeladmin, request, queryset):
    """
    Custom admin action to mark selected doctors as verified and send confirmation emails asynchronously.
    """
    # Fetch only the necessary fields to reduce memory usage
    doctors = queryset.select_related("user").only(
        "user__email", "user__full_name", "is_verified"
    )

    # Update the verification status in a single query
    updated_count = doctors.update(is_verified=True)

    # Send verification emails asynchronously using Celery
    for doctor in doctors.iterator():
        try:
            # Call the Celery task to send the email
            send_email_template.delay(
                subject="Doctor Verification Confirmation",
                template_name="emails/doctor_verified.html",
                context={
                    "doctor_name": doctor.user.full_name,
                    "support_email": "MediPoint@decodaai.com",
                    "support_phone": "+123456789",
                },
                to_email=doctor.user.email,
            )
        except Exception as e:
            # Log the error and continue with the next doctor
            messages.warning(
                request, f"Failed to schedule email for {doctor.user.email}: {str(e)}"
            )

    # Notify the admin of the successful verification
    messages.success(request, f"{updated_count} doctor(s) have been verified.")


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["user", "fees", "experience", "is_verified", "verify_toggle_button"]
    list_filter = ["specialty"]
    search_fields = ["user__full_name", "user__email"]
    actions = [verify_doctors]
    inlines = [ScheduleInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:doctor_id>/toggle-verify/",
                self.admin_site.admin_view(self.toggle_verify),
                name="doctors_doctor_toggle_verify",
            ),
        ]
        return custom_urls + urls

    def verify_toggle_button(self, obj):
        action_label = "Unverify" if obj.is_verified else "Verify"
        confirm_text = (
            f"Are you sure you want to {action_label.lower()} {obj.user.full_name}?"
        )
        url = reverse("admin:doctors_doctor_toggle_verify", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" onclick="return confirm(\'{}\');">{}</a>',
            url,
            confirm_text.replace("'", "\\'"),
            action_label,
        )

    verify_toggle_button.short_description = "Verify/Unverify"

    def toggle_verify(self, request, doctor_id):
        doctor = get_object_or_404(Doctor, pk=doctor_id)
        doctor.is_verified = not doctor.is_verified
        doctor.save(update_fields=["is_verified"])

        status_text = "verified" if doctor.is_verified else "unverified"
        messages.success(request, f"{doctor.user.full_name} has been {status_text}.")

        changelist_url = reverse("admin:doctors_doctor_changelist")
        return redirect(request.META.get("HTTP_REFERER", changelist_url))
