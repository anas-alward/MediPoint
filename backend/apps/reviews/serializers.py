from .models import Review, Comment
from rest_framework import serializers

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'patient', 'rating', 'content', 'appointment', 'created_at', 'updated_at']
        read_only_fields = ['patient', 'appointment', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["appointment"].read_only = True


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'review', 'type', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'type', "review",  'created_at', 'updated_at']