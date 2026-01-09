import django_filters
from .models import Doctor

class DoctorFilter(django_filters.FilterSet):
    # Add a filter for the 'specialty' field
    specialty = django_filters.CharFilter(field_name='specialty__slug', lookup_expr='icontains')
    # rating = django_filters.CharField(field_name=speciality )
    class Meta:
        model = Doctor
        fields = ['specialty']  # Specify the fields you want to filter on