from django.contrib import admin


from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    '''Admin View for Appointment'''

    list_display = ('patient', 'doctor', 'working_hours', 'fees', )
    list_filter = ('patient', 'doctor__user', 'working_hours')
    search_fields = ['patient', 'doctor']

