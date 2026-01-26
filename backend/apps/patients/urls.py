from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    PatientFolderSharedBulkView,
    PatientFolderSharedViewSet,
    PatientViewSet,
    PatientFolderViewSet,
    PatientFileViewSet,
    ProtectedMediaView,
)

router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patients")
router.register(r"folders", PatientFolderViewSet, basename="patient-folders")
router.register(r"files", PatientFileViewSet, basename="patient-files")
router.register(
    r"shared-folders", PatientFolderSharedViewSet, basename="patient-shared-folders"
)
patient_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
patient_router.register(r"folders", PatientFolderViewSet, basename="patient-folders")

folder_router = routers.NestedSimpleRouter(router, r"folders", lookup="folder")
folder_router.register(r"files", PatientFileViewSet, basename="patient-files")


urlpatterns = []
patient_routes = [
    path(
        "patient-folders/shared/bulk/",
        PatientFolderSharedBulkView.as_view(),
        name="patient-folder-shared-bulk",
    ),
    path("", include(router.urls)),
    path("", include(patient_router.urls)),
    path("", include(folder_router.urls)),
    # Serve protected files; requires file id in path so view can authorize ownership
    path(
        "protected-media/<int:id>/",
        ProtectedMediaView.as_view(),
        name="protected_media",
    ),
]
