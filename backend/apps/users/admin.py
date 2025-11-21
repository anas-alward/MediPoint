from django.contrib import admin
from .models import User 
from django.contrib.auth.hashers import make_password


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'email', 'full_name', 'gender']
    list_filter = ['role']
    search_fields = ['email','full_name']
    
    def save_model(self, request, obj, form, change):
        # Check if the password is being set or changed
        if 'password' in form.cleaned_data:
            raw_password = form.cleaned_data['password']
            
            # Check if the password starts with 'p2kpd'
            if not raw_password.startswith('pbkdf2_sha'):
                # Hash the password if it doesn't start with 'p2kpd'
                obj.password = make_password(raw_password)
            else:
                # Keep the password as is if it starts with 'p2kpd'
                obj.password = raw_password
        
        # Save the user object
        super().save_model(request, obj, form, change)