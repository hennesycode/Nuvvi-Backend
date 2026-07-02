from django.contrib import admin
from .models import ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "key_prefix", "is_active", "created_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("name", "tenant__name", "key_prefix")
    ordering = ("-created_at",)
    readonly_fields = ("key_prefix", "hashed_key", "created_at", "last_used_at")
