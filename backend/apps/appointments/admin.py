from django.contrib import admin


from .models import Appointment, Payment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    '''Admin View for Appointment'''

    list_display = ('patient', 'doctor', 'working_hours', 'fees', )
    list_filter = ('patient', 'doctor__user', 'working_hours')
    search_fields = ['patient', 'doctor']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    '''Admin View for Payment'''

    list_display = ('appointment', 'amount', 'currency', 'status', 'payment_type', )
    list_filter = ('status', 'payment_type', )
    search_fields = ['appointment', ] 