from django.contrib import admin
from django.contrib import messages

from apps.users.tasks import send_email_template
from .models import Doctor, Specialty, Schedule, WorkingHours
from .forms import ScheduleTabularInlineModelForm

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug':('name',)}
    

class ScheduleInline(admin.TabularInline):
    '''Tabular Inline View for Schedule'''
    model = Schedule
    form = ScheduleTabularInlineModelForm
    min_num = 0
    max_num = 10
    extra = 0



@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['start_time', 'end_time', 'day','doctor']
    
@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ['start_time', 'end_time','doctor']
    list_filter = ['doctor__user__full_name']
    search_fields = ['doctor']





@admin.action(description="Verify selected doctors")
def verify_doctors(modeladmin, request, queryset):
    """
    Custom admin action to mark selected doctors as verified and send confirmation emails asynchronously.
    """
    # Fetch only the necessary fields to reduce memory usage
    doctors = queryset.select_related("user").only("user__email", "user__full_name", "is_verified")

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
                to_email=doctor.user.email
            )
        except Exception as e:
            # Log the error and continue with the next doctor
            messages.warning(request, f"Failed to schedule email for {doctor.user.email}: {str(e)}")

    # Notify the admin of the successful verification
    messages.success(request, f"{updated_count} doctor(s) have been verified.")

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['user', 'fees', 'experience']
    list_filter = ['specialty']
    search_fields = ['user__full_name', 'user__email']
    actions = [verify_doctors]
    inlines = [
        ScheduleInline
    ]
    