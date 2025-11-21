from django.http import FileResponse, HttpResponse, Http404
from django.conf import settings
from django.shortcuts import get_object_or_404
import os

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .permissions import IsPatient, IsPatientOwnerOfFolderOrFile
from .models import Patient, PatientFolder, PatientFile
from .serializers import PatientFolderSerializer, PatientSerializer, PatientFileSerializer

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().select_related("user")
    serializer_class = PatientSerializer
    

    def get_serializer(self, *args, **kwargs):
        # Pass the request context to the serializer
        kwargs["context"] = {"request": self.request}
        return super().get_serializer(*args, **kwargs)


class PatientFolderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsPatient, IsPatientOwnerOfFolderOrFile]
    queryset = PatientFolder.objects.all().select_related("patient")
    serializer_class = PatientFolderSerializer
    http_method_names = ["get", "post", "put", "patch", "delete"]

    def get_queryset(self):
        patient_id = self.kwargs.get("patient_pk")
        folder_id = self.kwargs.get("pk")

        if patient_id: 
            self._handle_nested_patient_scenario(patient_id)
        elif folder_id:
            self._handle_direct_folder_access(folder_id)

        return super().get_queryset()

    def perform_create(self, serializer):
        patient_id = self.kwargs.get("patient_pk")
        if patient_id == "me":
            serializer.save(patient=self.request.user.patient)
        else:
            patient = Patient.objects.get(pk=patient_id)
            serializer.save(patient=patient)

    def _handle_nested_patient_scenario(self, patient_id):
        """Filter folders for a specific patient (nested under /patients/ endpoint)"""
        if patient_id == "me":
            self.queryset = self.queryset.filter(patient=self.request.user.patient)
        elif patient_id.isdigit():
            self.queryset = self.queryset.filter(patient_id=patient_id)
        else:
            self.queryset = self.queryset.none()

    def _handle_direct_folder_access(self, folder_id):
        """Filter for direct folder access (not nested under patient)"""
        self.queryset = self.queryset.filter(id=folder_id)


class PatientFileViewSet(viewsets.ModelViewSet):
    queryset = PatientFile.objects.all().select_related("folder")
    serializer_class = PatientFileSerializer
    permission_classes = [IsAuthenticated, IsPatient, IsPatientOwnerOfFolderOrFile]

    def get_queryset(self):
        folder_id = self.kwargs.get("folder_pk")
        file_id = self.kwargs.get("pk")

        qs = self.queryset  # start with the base queryset

        if folder_id:
            folder = get_object_or_404(PatientFolder, id=folder_id)
            qs = qs.filter(folder=folder)
        elif file_id:
            qs = qs.filter(id=file_id)
        else:
            qs = qs.none()

        return qs  # MUST return the queryset

    def perform_create(self, serializer):
        folder_id = self.kwargs.get("folder_pk")
        folder = get_object_or_404(PatientFolder, id=folder_id)
        serializer.save(folder=folder)


class ProtectedMediaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        # Remove leading slashes and normalize path

        # Try to find the PatientFile object that references this file
        # id = id.split('.')[0]
        try:
            patient_file = PatientFile.objects.get(id=id)
        except PatientFile.DoesNotExist:
            raise Http404("File not found")

        
        if  not request.user.is_patient or patient_file.folder.patient != request.user.patient:
            return Response({"detail": "Forbidden"}, status=403)
            
        
        # Serve the file
        file_path = patient_file.file.path
        if not os.path.exists(file_path):
            raise Http404("File missing on disk")

        if settings.SERVE_PROTECTED_MEDIA_DIRECT:
            # DEV mode: serve through Django
            return FileResponse(open(file_path, "rb"))
        else:
            # PROD mode: tell Nginx to serve it
            protected_path = (
                f"/media/{settings.PROTECTED_SUBPATH}/{patient_file.name}"
            )
            response = HttpResponse()
            response["Content-Type"] = ""
            response["X-Accel-Redirect"] = protected_path
            return response
