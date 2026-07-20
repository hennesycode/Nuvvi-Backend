from rest_framework import serializers

from apps.dian.matias_service import get_connection, get_records, matias_request
from apps.dian.models import MatiasConnection

from .models import Company, CompanyProviderLink, CompanySyncAttempt
from .services import normalize_email, normalize_nit, remote_records


class CompanyProviderLinkSerializer(serializers.ModelSerializer):
    provider_status_label = serializers.CharField(source="get_provider_status_display", read_only=True)

    class Meta:
        model = CompanyProviderLink
        fields = ["id", "provider", "environment", "parent_company_uuid", "matias_company_id", "matias_client_uuid", "remote_name", "remote_nit", "remote_email", "provider_status", "provider_status_label", "enabled_in_provider", "last_sync_at", "last_success_at", "last_error_code", "last_error_message", "last_remote_snapshot"]


class CompanySyncAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySyncAttempt
        fields = ["id", "operation", "request_identifier", "http_method", "endpoint", "http_status", "successful", "error_code", "error_message", "response_time_ms", "created_at"]


class CompanySerializer(serializers.ModelSerializer):
    provider_link = serializers.SerializerMethodField()
    recent_attempts = serializers.SerializerMethodField()
    local_status_label = serializers.CharField(source="get_local_status_display", read_only=True)
    onboarding_status_label = serializers.CharField(source="get_onboarding_status_display", read_only=True)

    class Meta:
        model = Company
        fields = ["id", "legal_name", "nit", "email", "owner_first_name", "owner_last_name", "country_id", "department_id", "city_id", "address", "mobile", "phone", "notes", "assigned_executive", "local_status", "local_status_label", "onboarding_status", "onboarding_status_label", "created_by", "created_at", "updated_at", "archived_at", "provider_link", "recent_attempts"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "archived_at", "provider_link", "recent_attempts", "local_status_label", "onboarding_status_label"]

    def get_provider_link(self, obj):
        environment = self.context.get("environment") or MatiasConnection.ENVIRONMENT_SANDBOX
        link = obj.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=environment).first()
        return CompanyProviderLinkSerializer(link).data if link else None

    def get_recent_attempts(self, obj):
        return CompanySyncAttemptSerializer(obj.sync_attempts.all()[:8], many=True).data


class CompanyCreateSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=80)
    company_name = serializers.CharField(max_length=255)
    nit = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=120)
    last_name = serializers.CharField(max_length=120)
    country_id = serializers.CharField(max_length=50)
    department_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    city_id = serializers.CharField(max_length=50)
    address = serializers.CharField(max_length=255)
    mobile = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(write_only=True, trim_whitespace=False)
    environment = serializers.ChoiceField(choices=MatiasConnection.ENVIRONMENT_CHOICES, default=MatiasConnection.ENVIRONMENT_SANDBOX)

    def validate(self, attrs):
        attrs["nit"] = normalize_nit(attrs["nit"])
        attrs["email"] = normalize_email(attrs["email"])
        if not attrs["nit"]:
            raise serializers.ValidationError({"nit": "El NIT es obligatorio."})
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": "Las contraseñas no coinciden."})
        if not attrs["password"]:
            raise serializers.ValidationError({"password": "La contraseña temporal es obligatoria."})
        catalogs = fetch_catalogs(attrs.get("environment", MatiasConnection.ENVIRONMENT_SANDBOX))
        countries = {str(item.get("id") or item.get("value") or item.get("code") or item.get("uuid") or "") for item in catalogs["countries"]}
        departments = {str(item.get("id") or item.get("value") or item.get("code") or item.get("uuid") or "") for item in catalogs["departments"]}
        cities = {str(item.get("id") or item.get("value") or item.get("code") or item.get("uuid") or "") for item in catalogs["cities"]}
        if countries and str(attrs["country_id"]) not in countries:
            raise serializers.ValidationError({"country_id": "El país no existe en el catálogo MATIAS sincronizado."})
        if attrs.get("department_id") and departments and str(attrs["department_id"]) not in departments:
            raise serializers.ValidationError({"department_id": "El departamento no existe en el catálogo MATIAS sincronizado."})
        if cities and str(attrs["city_id"]) not in cities:
            raise serializers.ValidationError({"city_id": "La ciudad no existe en el catálogo MATIAS sincronizado."})
        selected_city = next((item for item in catalogs["cities"] if str(item.get("id") or item.get("value") or item.get("code") or item.get("uuid") or "") == str(attrs["city_id"])), None)
        city_department = str((selected_city or {}).get("department_id") or (selected_city or {}).get("department") or (selected_city or {}).get("departmentId") or "")
        if attrs.get("department_id") and city_department and city_department != str(attrs["department_id"]):
            raise serializers.ValidationError({"city_id": "La ciudad no corresponde al departamento seleccionado."})
        return attrs


class CompanyUpdateSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255, required=False)
    nit = serializers.CharField(max_length=50, required=False)
    email = serializers.EmailField(required=False)
    owner_first_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    owner_last_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    department_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    city_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    mobile = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    assigned_executive = serializers.CharField(max_length=120, required=False, allow_blank=True)
    environment = serializers.ChoiceField(choices=MatiasConnection.ENVIRONMENT_CHOICES, default=MatiasConnection.ENVIRONMENT_SANDBOX)

    def validate_nit(self, value):
        return normalize_nit(value)

    def validate_email(self, value):
        return normalize_email(value)


class CompanySettingSerializer(serializers.Serializer):
    setting_key = serializers.CharField(max_length=120)
    setting_value = serializers.CharField(allow_blank=True)
    environment = serializers.ChoiceField(choices=MatiasConnection.ENVIRONMENT_CHOICES, default=MatiasConnection.ENVIRONMENT_SANDBOX)


class MatiasCatalogSerializer(serializers.Serializer):
    environment = serializers.ChoiceField(choices=MatiasConnection.ENVIRONMENT_CHOICES, default=MatiasConnection.ENVIRONMENT_SANDBOX)


def fetch_catalogs(environment):
    connection = get_connection(environment)
    catalogs = {}
    for key, endpoint in (("countries", "/countries"), ("departments", "/departments"), ("cities", "/cities")):
        response = matias_request(connection, endpoint)
        catalogs[key] = get_records(response["data"]) if response["ok"] else []
    return catalogs
