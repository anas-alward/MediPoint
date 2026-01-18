from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import PatientReport


@receiver(post_save, sender=PatientReport)
def deactivate_patient_after_ten_reports(sender, instance, created, **kwargs):
    if not created:
        return

    now = timezone.now()
    start_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_next_month = start_current_month + relativedelta(months=1)

    report_count = PatientReport.objects.filter(
        patient=instance.patient,
        created_at__gte=start_current_month,
        created_at__lt=start_next_month,
    ).count()

    patient_user = instance.patient.user
    if report_count >= 10 and patient_user.is_active:
        patient_user.is_active = False
        patient_user.save(update_fields=["is_active"])
