from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.users.models import User
from apps.users.serializers import UserSerializer
from apps.doctors.models import Doctor
from apps.patients.models import Patient


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        request = self.context["request"]

        # Step 1: Call parent validate to set self.user
        data = super().validate(attrs)  # ✅ self.user is now available
        print("HI")
        # Block login for inactive or unverified accounts
        if not self.user.is_active:
            raise ValidationError("Account is inactive.")
        if not self.user.is_email_verified:
            raise ValidationError(
                "Email is not verified. Please verify your email before logging in."
            )

        # Step 2: Ensure a session exists
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key

        # Step 3: Create tokens manually
        refresh = self.get_token(self.user)  # now self.user exists
        access = refresh.access_token

        # Step 4: Inject claims
        refresh["role"] = self.user.role
        refresh["sessionid"] = session_id
        access["role"] = self.user.role
        access["sessionid"] = session_id
        # Step 5: Override default token strings in response
        data["refresh"] = str(refresh)
        data["access"] = str(access)

        # Step 6: Add extra info to response

        data["user"] = UserSerializer(self.user).data
        data["sessionid"] = session_id

        return data


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True, validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    password2 = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role", "password", "password2")

    def validate(self, data):
        """Ensure passwords match"""
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return data

    def create(self, validated_data):
        """Create a new user with hashed password"""
        validated_data.pop(
            "password2"
        )  # Remove password2 since it's unnecessary for user creation
        user = User.objects.create_user(**validated_data)
        return user


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data["email"].lower()
        cache_key = f"email_verification_otp:{email}"
        cached_otp = cache.get(cache_key)

        if not cached_otp or str(data["otp"]).strip() != str(cached_otp):
            raise ValidationError("Invalid or expired OTP.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid user.")

        data["user"] = user
        data["cache_key"] = cache_key
        return data


class EmailVerificationResendSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, data):
        email = data["email"].lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid user.")

        if user.is_email_verified:
            raise ValidationError("Email already verified.")

        data["user"] = user
        data["email"] = email
        return data


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def update(self, instance, validated_data):
        instance.set_password(validated_data["new_password"])
        instance.save()
        return instance


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        email = data["email"].lower()
        cache_key = f"password_reset_otp:{email}"
        cached_otp = cache.get(cache_key)

        if not cached_otp or str(data["otp"]).strip() != str(cached_otp):
            raise ValidationError("Invalid or expired OTP.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid user.")

        data["user"] = user
        data["cache_key"] = cache_key
        return data


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, data):
        email = data["email"].lower()
        cache_key = f"password_reset_token:{email}"
        cached_token = cache.get(cache_key)

        if not cached_token or data["token"].strip() != str(cached_token):
            raise ValidationError("Invalid or expired token.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid user.")

        validate_password(data["new_password"])

        data["user"] = user
        data["cache_key"] = cache_key
        return data


class DoctorMeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="user.id", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", required=False)
    image = serializers.ImageField(source="user.image", required=False, allow_null=True)
    gender = serializers.CharField(
        source="user.gender", required=False, allow_blank=True, allow_null=True
    )
    dob = serializers.DateField(source="user.dob", required=False, allow_null=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "role",
            "email",
            "full_name",
            "image",
            "gender",
            "dob",
            "fees",
            "experience",
            "education",
            "about",
            "status",
            "specialty",
            "address_line1",
            "address_line2",
            "is_verified",
            "degree_document",
            "rating",
            "reviewers_num",
        ]
        read_only_fields = ["is_verified", "rating", "reviewers_num"]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        for attr, value in user_data.items():
            setattr(instance.user, attr, value)

        if user_data:
            instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class PatientMeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="user.id", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", required=False)
    image = serializers.ImageField(source="user.image", required=False, allow_null=True)
    gender = serializers.CharField(
        source="user.gender", required=False, allow_blank=True, allow_null=True
    )
    dob = serializers.DateField(source="user.dob", required=False, allow_null=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "role",
            "email",
            "full_name",
            "image",
            "gender",
            "dob",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        for attr, value in user_data.items():
            setattr(instance.user, attr, value)

        if user_data:
            instance.user.save()

        instance.save()
        return instance
