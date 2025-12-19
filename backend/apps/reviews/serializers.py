from .models import Review, Comment
from rest_framework import serializers


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'review', 'type', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'type', "review",  'created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    class Meta:
        model = Review
        fields = ['id', 'patient', 'rating', 'content', 'doctor', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['patient', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["doctor"].read_only = True