from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter
from django.urls import path, include

from .views import ReviewsViewSet, CommentsViewSet

router = DefaultRouter()
router.register(r'reviews', ReviewsViewSet, basename='reviews')
router.register(r"comments", CommentsViewSet, basename="comments")

reviews_router = NestedDefaultRouter(router, r'reviews', lookup='review')
reviews_router.register(r'comments', CommentsViewSet, basename='review-comments')


reviews_routes = [
    path('', include(router.urls)),
    path('', include(reviews_router.urls)),
]
