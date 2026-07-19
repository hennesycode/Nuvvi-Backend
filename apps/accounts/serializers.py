from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


def validate_unique_user_field(instance, field: str, value: str, message: str):
    if not value:
        return value
    lookup = {f"{field}__iexact": value}
    queryset = User.objects.filter(**lookup)
    if instance:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise serializers.ValidationError(message)
    return value


def normalize_username(value: str) -> str:
    username = (value or "").strip().lower()
    if len(username) < 3:
        raise serializers.ValidationError("El nombre de usuario debe tener mínimo 3 caracteres.")
    if not all(char.isalnum() or char in "._-" for char in username):
        raise serializers.ValidationError("Usa solo letras, números, punto, guion o guion bajo.")
    return username


class UserSerializer(serializers.ModelSerializer):
    admin_role_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "full_name", "first_name", "last_name", "admin_role", "admin_role_label",
            "identification_type", "identification_number", "country", "department", "city", "address",
            "phone_country_code", "phone_number", "last_login", "invitation_sent_at", "is_active",
            "is_staff", "is_superuser", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_admin_role_label(self, obj):
        if obj.admin_role:
            return obj.get_admin_role_display()
        if obj.is_staff or obj.is_superuser:
            return "Superadministrador"
        return ""


class AdminUserSerializer(serializers.ModelSerializer):
    admin_role_label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "full_name", "username", "admin_role", "admin_role_label", "identification_type",
            "identification_number", "email", "country", "department", "city", "address",
            "phone_country_code", "phone_number", "is_active", "is_superuser", "is_staff",
            "last_login", "invitation_sent_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "full_name", "is_superuser", "is_staff", "last_login", "invitation_sent_at", "created_at", "updated_at"]

    def get_admin_role_label(self, obj):
        if obj.admin_role:
            return obj.get_admin_role_display()
        if obj.is_staff or obj.is_superuser:
            return "Superadministrador"
        return ""

    def validate(self, attrs):
        data = {**getattr(self.instance, "__dict__", {}), **attrs}
        required_fields = [
            "first_name", "last_name", "username", "admin_role", "identification_type", "identification_number",
            "email", "department", "city", "address", "phone_number",
        ]
        missing = [field for field in required_fields if not str(data.get(field, "")).strip()]
        if missing:
            raise serializers.ValidationError({field: "Este campo es obligatorio." for field in missing})

        if attrs.get("admin_role") not in dict(User.ADMIN_ROLE_CHOICES):
            raise serializers.ValidationError({"admin_role": "Selecciona un rol válido."})
        if attrs.get("identification_type") not in dict(User.IDENTIFICATION_TYPE_CHOICES):
            raise serializers.ValidationError({"identification_type": "Selecciona un tipo de identificación válido."})

        username = normalize_username(str(data.get("username", "")))
        validate_unique_user_field(self.instance, "username", username, "Este nombre de usuario ya está registrado.")
        attrs["username"] = username

        email = User.objects.normalize_email(str(data.get("email", "")).strip())
        validate_unique_user_field(self.instance, "email", email, "Este correo ya está registrado.")
        attrs["email"] = email

        identification_number = str(data.get("identification_number", "")).strip()
        phone_number = str(data.get("phone_number", "")).strip()
        if not identification_number.isdigit():
            raise serializers.ValidationError({"identification_number": "El documento debe contener solo números."})
        validate_unique_user_field(self.instance, "identification_number", identification_number, "Este número de identificación ya está registrado.")
        attrs["identification_number"] = identification_number
        if not phone_number.isdigit() or len(phone_number) != 10:
            raise serializers.ValidationError({"phone_number": "El celular debe tener exactamente 10 números."})
        if data.get("country") and data.get("country") != "Colombia":
            raise serializers.ValidationError({"country": "Por ahora solo se permite Colombia."})
        return attrs

    def create(self, validated_data):
        validated_data["full_name"] = f"{validated_data['first_name'].strip()} {validated_data['last_name'].strip()}".strip()
        validated_data["country"] = "Colombia"
        validated_data["phone_country_code"] = "+57"
        validated_data["is_staff"] = True
        validated_data["is_superuser"] = validated_data["admin_role"] == User.ROLE_SUPERADMIN
        user = User(**validated_data)
        user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.full_name = f"{instance.first_name.strip()} {instance.last_name.strip()}".strip()
        instance.country = "Colombia"
        instance.phone_country_code = "+57"
        instance.is_staff = True
        instance.is_superuser = instance.admin_role == User.ROLE_SUPERADMIN
        instance.save()
        return instance


class PasswordSetupSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden."})
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "username", "identification_type", "identification_number", "email",
            "country", "department", "city", "address", "phone_country_code", "phone_number",
        ]

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        return validate_unique_user_field(self.instance, "email", email, "Este correo ya está registrado.")

    def validate_username(self, value):
        username = normalize_username(value)
        return validate_unique_user_field(self.instance, "username", username, "Este nombre de usuario ya está registrado.")

    def validate_identification_number(self, value):
        identification_number = str(value).strip()
        if not identification_number.isdigit():
            raise serializers.ValidationError("El documento debe contener solo números.")
        return validate_unique_user_field(self.instance, "identification_number", identification_number, "Este número de identificación ya está registrado.")

    def validate(self, attrs):
        data = {**getattr(self.instance, "__dict__", {}), **attrs}
        required_fields = [
            "first_name", "last_name", "username", "identification_type", "identification_number",
            "email", "department", "city", "address", "phone_number",
        ]
        missing = [field for field in required_fields if not str(data.get(field, "")).strip()]
        if missing:
            raise serializers.ValidationError({field: "Este campo es obligatorio." for field in missing})

        if data.get("identification_type") not in dict(User.IDENTIFICATION_TYPE_CHOICES):
            raise serializers.ValidationError({"identification_type": "Selecciona un tipo de identificación válido."})

        phone_number = str(data.get("phone_number", "")).strip()
        if not phone_number.isdigit() or len(phone_number) != 10:
            raise serializers.ValidationError({"phone_number": "El celular debe tener exactamente 10 números."})
        if data.get("country") and data.get("country") != "Colombia":
            raise serializers.ValidationError({"country": "Por ahora solo se permite Colombia."})
        return attrs

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.full_name = f"{instance.first_name.strip()} {instance.last_name.strip()}".strip()
        instance.country = "Colombia"
        instance.phone_country_code = "+57"
        instance.save()
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden."})
        validate_password(attrs["password"], self.context["request"].user)
        return attrs


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer(source="*", read_only=True)
