from rest_framework.viewsets import ModelViewSet
from .models import Review, Comment
from .serializers import ReviewSerializer, CommentSerializer
from .permissions import IsReviewOwnerOrReadOnly, IsCommentOwner
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import NotFound

class ReviewsViewSet(ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsReviewOwnerOrReadOnly]

    
    def get_queryset(self):
        if self.kwargs.get("appointment_pk"):                
            return super().get_queryset().filter(appointment_id=self.kwargs.get("appointment_pk"))
            
            
        return super().get_queryset()

    def perform_create(self, serializer):
        appointment_pk = self.kwargs.get("appointment_pk")
        if appointment_pk and appointment_pk.isdigit():
            try:
                appointment = Review.objects.get(pk=appointment_pk)
            except Review.DoesNotExist:
                raise NotFound("Appointment not found.")

            if appointment.patient != self.request.user.patient:
                raise PermissionDenied("You can only review your own appointments.")
            serializer.save(appointment_id=appointment, patient=self.request.user.patient)
        else:
            raise ValueError("Appointment ID is required to create a review.")


class CommentsViewSet(ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsCommentOwner]

    def perform_create(self, serializer):
        review_id = self.kwargs.get("review_pk")
        review = get_object_or_404(Review, pk=review_id)       
        serializer.save(user=self.request.user, review=review, type=self.request.user.role)

    def get_queryset(self):
        review_id = self.kwargs.get("review_pk")
        if review_id:
            return self.queryset.filter(review_id=review_id)
        
        return self.queryset
