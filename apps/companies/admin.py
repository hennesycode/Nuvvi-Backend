from django.contrib import admin

from .models import Company, CompanyProviderLink, CompanySyncAttempt


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "nit", "email", "local_status", "onboarding_status", "created_at")
    search_fields = ("legal_name", "nit", "email")
    list_filter = ("local_status", "onboarding_status")


@admin.register(CompanyProviderLink)
class CompanyProviderLinkAdmin(admin.ModelAdmin):
    list_display = ("company", "provider", "environment", "provider_status", "matias_company_id", "matias_client_uuid", "last_sync_at")
    search_fields = ("company__legal_name", "remote_nit", "remote_email", "matias_company_id", "matias_client_uuid")
    list_filter = ("provider", "environment", "provider_status", "enabled_in_provider")


@admin.register(CompanySyncAttempt)
class CompanySyncAttemptAdmin(admin.ModelAdmin):
    list_display = ("operation", "company", "http_method", "http_status", "successful", "created_at")
    search_fields = ("company__legal_name", "request_identifier", "endpoint", "error_message")
    list_filter = ("operation", "successful")
