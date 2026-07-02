from django.contrib import admin
from .models import Tenant, TenantUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "legal_name", "nit", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "legal_name", "nit", "email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ("tenant", "user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("tenant__name", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
