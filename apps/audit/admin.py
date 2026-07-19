from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity", "entity_id", "status", "actor", "ip_address", "created_at")
    list_filter = ("status", "action", "entity")
    search_fields = ("actor__email", "actor__username", "actor__identification_number", "tenant__name", "entity", "entity_id", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
