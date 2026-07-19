from rest_framework import serializers

from .matias_service import get_default_url, mask_token
from .models import MatiasConnection


class MatiasConnectionSerializer(serializers.ModelSerializer):
    token_preview = serializers.SerializerMethodField()
    environment_label = serializers.CharField(source="get_environment_display", read_only=True)
    default_base_url = serializers.SerializerMethodField()

    class Meta:
        model = MatiasConnection
        fields = [
            "id", "name", "environment", "environment_label", "base_url", "default_base_url", "enabled",
            "timeout_seconds", "retry_attempts", "auth_method", "token_preview", "token_external_id",
            "token_name", "token_expires_at", "account_email", "parent_company_uuid", "external_company_id",
            "external_company_name", "external_company_nit", "account_main_email", "linked_companies_count",
            "connection_status", "operational_status", "environment_detected", "multicompany_verified",
            "last_test_at", "last_success_at", "last_error_at", "last_error_code", "last_error_message",
            "last_response_time_ms", "last_test_results", "catalogs_status", "catalogs_synced_count",
            "catalogs_total_count", "catalogs_last_synced_at", "catalogs_detail", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "auth_method", "token_preview", "external_company_id", "external_company_name", "external_company_nit",
            "account_main_email", "linked_companies_count", "connection_status", "operational_status",
            "environment_detected", "multicompany_verified", "last_test_at", "last_success_at", "last_error_at",
            "last_error_code", "last_error_message", "last_response_time_ms", "last_test_results", "catalogs_status",
            "catalogs_synced_count", "catalogs_total_count", "catalogs_last_synced_at", "catalogs_detail", "created_at", "updated_at",
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
        base_url = attrs.get("base_url", getattr(self.instance, "base_url", ""))
        environment = attrs.get("environment", getattr(self.instance, "environment", MatiasConnection.ENVIRONMENT_SANDBOX))
        if not str(base_url).startswith("https://"):
            raise serializers.ValidationError({"base_url": "La URL base debe usar HTTPS."})
        if environment not in dict(MatiasConnection.ENVIRONMENT_CHOICES):
            raise serializers.ValidationError({"environment": "Ambiente inválido."})
        return attrs


class MatiasTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField(write_only=True)
    token_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    token_external_id = serializers.CharField(required=False, allow_blank=True, max_length=120)
    token_expires_at = serializers.DateTimeField(required=False, allow_null=True)
    account_email = serializers.EmailField(required=False, allow_blank=True)


class MatiasGeneratePatSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    token_name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
    expires_in_days = serializers.IntegerField(min_value=1, max_value=365, default=90)
