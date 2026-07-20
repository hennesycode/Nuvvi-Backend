from rest_framework import serializers

from .matias_service import get_default_url, mask_token, normalize_base_url
from .models import MatiasConnection


class MatiasConnectionSerializer(serializers.ModelSerializer):
    token_preview = serializers.SerializerMethodField()
    environment_label = serializers.CharField(source="get_environment_display", read_only=True)
    default_base_url = serializers.SerializerMethodField()

    class Meta:
        model = MatiasConnection
        fields = [
            "id", "name", "environment", "environment_label", "base_url", "default_base_url", "enabled",
            "timeout_seconds", "retry_attempts", "token_generation_endpoint", "auth_method", "token_preview", "token_external_id",
            "token_name", "token_expires_at", "token_created_at", "authenticated_user_id", "authenticated_user_email", "account_email", "parent_company_uuid", "external_company_id",
            "external_company_name", "external_company_nit", "account_main_email", "linked_companies_count",
            "external_company_status", "membership_plan", "membership_status", "membership_expires_at",
            "membership_documents_available", "membership_documents_consumed", "membership_company_limit", "membership_summary",
            "connection_status", "operational_status", "environment_detected", "multicompany_verified",
            "last_test_at", "last_success_at", "last_error_at", "last_error_code", "last_error_message",
            "last_response_time_ms", "last_test_results", "catalogs_status", "catalogs_synced_count",
            "catalogs_total_count", "catalogs_last_attempt_at", "catalogs_last_synced_at", "catalogs_detail", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "auth_method", "token_preview", "token_external_id", "token_expires_at", "token_created_at", "authenticated_user_id", "authenticated_user_email", "external_company_id", "external_company_name", "external_company_nit",
            "account_main_email", "linked_companies_count", "external_company_status", "membership_plan", "membership_status", "membership_expires_at", "membership_documents_available", "membership_documents_consumed", "membership_company_limit", "membership_summary", "connection_status", "operational_status",
            "environment_detected", "multicompany_verified", "last_test_at", "last_success_at", "last_error_at",
            "last_error_code", "last_error_message", "last_response_time_ms", "last_test_results", "catalogs_status",
            "catalogs_synced_count", "catalogs_total_count", "catalogs_last_attempt_at", "catalogs_last_synced_at", "catalogs_detail", "created_at", "updated_at",
        ]

    def get_token_preview(self, obj):
        from .matias_service import decrypt_secret

        try:
            return mask_token(decrypt_secret(obj.encrypted_access_token))
        except Exception:
            return "Token cifrado no legible"

    def get_default_base_url(self, obj):
        return get_default_url(obj.environment)

    def validate(self, attrs):
        base_url = normalize_base_url(attrs.get("base_url", getattr(self.instance, "base_url", "")))
        environment = attrs.get("environment", getattr(self.instance, "environment", MatiasConnection.ENVIRONMENT_SANDBOX))
        token_generation_endpoint = attrs.get("token_generation_endpoint", getattr(self.instance, "token_generation_endpoint", "/tokens"))
        timeout_seconds = attrs.get("timeout_seconds", getattr(self.instance, "timeout_seconds", 20))
        retry_attempts = attrs.get("retry_attempts", getattr(self.instance, "retry_attempts", 2))
        if not str(base_url).startswith("https://"):
            raise serializers.ValidationError({"base_url": "La URL base debe usar HTTPS."})
        attrs["base_url"] = base_url
        if environment not in dict(MatiasConnection.ENVIRONMENT_CHOICES):
            raise serializers.ValidationError({"environment": "Ambiente inválido."})
        if not isinstance(attrs.get("enabled", getattr(self.instance, "enabled", False)), bool):
            raise serializers.ValidationError({"enabled": "Integración activa debe ser booleano."})
        if not 5 <= int(timeout_seconds) <= 120:
            raise serializers.ValidationError({"timeout_seconds": "El timeout debe estar entre 5 y 120 segundos."})
        if int(retry_attempts) < 0:
            raise serializers.ValidationError({"retry_attempts": "Los reintentos deben ser un entero no negativo."})
        if not str(token_generation_endpoint).startswith("/"):
            raise serializers.ValidationError({"token_generation_endpoint": "El endpoint de creación PAT debe iniciar con /."})
        return attrs


class MatiasTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField(write_only=True)
    token_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    account_email = serializers.EmailField(required=False, allow_blank=True)


class MatiasGeneratePatSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    token_name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
    expires_in_days = serializers.IntegerField(min_value=1, max_value=365, default=90)
