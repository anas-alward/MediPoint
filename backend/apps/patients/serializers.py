from rest_framework import serializers
from .models import Patient, PatientFolder, PatientFile, PatientSharedFolder
from apps.users.serializers import UserSerializer


class PatientSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)

    class Meta:
        model = Patient
        fields = ["user"]

    def update(self, instance, validated_data):
        # Handle nested user updates
        user_data = validated_data.pop("user", None)
        if user_data:
            user_serializer = UserSerializer(
                instance.user, data=user_data, partial=True
            )
            if user_serializer.is_valid():
                user_serializer.save()
        else:
            raise serializers.ValidationError("User object does not exists")

        instance.save()
        return instance


class PatientFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientFolder
        fields = ["id", "name", "description", "patient", "created_at", "updated_at"]
        read_only_fields = ["id", "patient", "created_at", "updated_at"]


class PatientFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientFile
        fields = ["id", "name", "file", "folder", "created_at", "updated_at"]
        read_only_fields = ["id", "folder", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super(PatientFileSerializer, self).__init__(*args, **kwargs)

        # If we are updating (the instance is present)
        if self.instance is not None:
            self.fields["name"].required = False
            self.fields["file"].required = False


class PatientFolderSharedSerializer(serializers.ModelSerializer):
    folder = serializers.PrimaryKeyRelatedField(
        source="folder",
        queryset=PatientFolder.objects.all(),
        write_only=True,
    )

    class Meta:
        model = PatientSharedFolder
        fields = [
            "folder",
            "doctor",
            "appointment",
            "sharing_type",
        ]

    def validate_folder(self, folder):
        request = self.context["request"]
        user = request.user

        if not hasattr(user, "patient"):
            raise serializers.ValidationError("Only patients can share folders.")

        if folder.patient != user.patient:
            raise serializers.ValidationError("You do not own this folder.")

        return folder



class PatientFolderSharedBulkCreateSerializer(serializers.Serializer):
    folder_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1)
    )
    sharing_type = serializers.ChoiceField(
        choices=PatientSharedFolder.SharingType.choices
    )
    doctor_id = serializers.IntegerField(required=False)
    appointment_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not hasattr(user, "patient"):
            raise serializers.ValidationError("Only patients can share folders.")

        if not attrs.get("doctor_id") and not attrs.get("appointment_id"):
            raise serializers.ValidationError("Either doctor_id or appointment_id must be provided.")

        # Validate folders belong to the patient
        folders = PatientFolder.objects.filter(
            id__in=attrs["folder_ids"], patient=user.patient
        )
        if len(folders) != len(attrs["folder_ids"]):
            owned_ids = set(f.id for f in folders)
            invalid_ids = [fid for fid in attrs["folder_ids"] if fid not in owned_ids]
            raise serializers.ValidationError(f"You do not own folders: {invalid_ids}")
        
        attrs["folders"] = folders
        return attrs

    def create(self):
        validated = self.validated_data
        folders = validated.pop("folders")
        shared_objects = []

        for folder in folders:
            shared_objects.append(
                PatientSharedFolder(
                    folder=folder,
                    sharing_type=validated["sharing_type"],
                    doctor_id=validated.get("doctor_id"),
                    appointment_id=validated.get("appointment_id")
                )
            )
        return PatientSharedFolder.objects.bulk_create(shared_objects, ignore_conflicts=True)


class PatientFolderSharedBulkRemoveSerializer(serializers.Serializer):
    shared_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1)
    )

    def validate_shared_ids(self, shared_ids):
        user = self.context["request"].user
        # Ensure user owns these shared folder records
        owned = PatientSharedFolder.objects.filter(
            id__in=shared_ids,
            folder__patient=user.patient
        ).values_list("id", flat=True)
        invalid = [sid for sid in shared_ids if sid not in owned]
        if invalid:
            raise serializers.ValidationError(f"You do not own shared folders: {invalid}")
        return shared_ids

    def delete(self):
        ids = self.validated_data["shared_ids"]
        deleted_count, _ = PatientSharedFolder.objects.filter(id__in=ids).delete()
        return deleted_count
