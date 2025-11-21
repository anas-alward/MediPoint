from django import forms
from .models import Schedule
from django.core.exceptions import ValidationError

class ScheduleTabularInlineModelForm(forms.ModelForm):
    start_time = forms.TimeField(
        widget=forms.TimeInput(format='%I:%M %p', attrs={'placeholder': 'HH:MM AM/PM'}),
        input_formats=['%I:%M %p', '%I:%M%p', '%H:%M'],  # Accepts both AM/PM and 24-hour formats
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(format='%I:%M %p', attrs={'placeholder': 'HH:MM AM/PM'}),
        input_formats=['%I:%M %p', '%I:%M%p', '%H:%M'],  # Accepts both AM/PM and 24-hour formats
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        # Validate that end_time is after start_time
        if start_time and end_time and end_time <= start_time:
            raise ValidationError("End time must be after the start time.")

        return cleaned_data

    class Meta:
        model = Schedule
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required
        for field in self.fields:
            self.fields[field].required = True