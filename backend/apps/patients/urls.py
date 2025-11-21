from django.urls import path, include
from rest_framework_nested import routers
from .views import PatientViewSet, PatientFolderViewSet, PatientFileViewSet, ProtectedMediaView

router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patients")
router.register(r"folders", PatientFolderViewSet, basename="patient-folders")
router.register(r"files", PatientFileViewSet, basename="patient-files")

patient_router = routers.NestedSimpleRouter(router, r'patients', lookup='patient')
patient_router.register(r"folders", PatientFolderViewSet, basename="patient-folders")

folder_router = routers.NestedSimpleRouter(router, r'folders', lookup='folder')
folder_router.register(r"files", PatientFileViewSet, basename="patient-files")


patient_routes = [
    path("", include(router.urls)),
    path("", include(patient_router.urls)),
    path("", include(folder_router.urls)),
    path("protected-media/", ProtectedMediaView.as_view(), name="protected_media"),
]
