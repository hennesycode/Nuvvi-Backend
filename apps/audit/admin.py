from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity", "entity_id", "actor", "tenant", "created_at")
    list_filter = ("action", "entity")
    search_fields = ("actor__email", "tenant__name", "entity", "entity_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
