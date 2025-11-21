from django.contrib import admin
from .models import Review, Comment


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'patient', 'rating')
    list_filter = ('doctor', 'patient', 'rating')
    
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user')
    list_filter = ('review', 'user')

