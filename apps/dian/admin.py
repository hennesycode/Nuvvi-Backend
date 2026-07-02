from django.contrib import admin
from .models import DianEnvironment, IssuerCompany, DianDocumentLog


@admin.register(DianEnvironment)
class DianEnvironmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(IssuerCompany)
class IssuerCompanyAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "nit", "tenant", "dian_environment", "is_active", "created_at")
    list_filter = ("is_active", "dian_environment")
    search_fields = ("legal_name", "nit", "tenant__name")
    readonly_fields = ("created_at",)


@admin.register(DianDocumentLog)
class DianDocumentLogAdmin(admin.ModelAdmin):
    list_display = ("document_type", "external_id", "status", "tenant", "created_at")
    list_filter = ("status", "document_type")
    search_fields = ("external_id", "tenant__name")
    readonly_fields = ("created_at",)
