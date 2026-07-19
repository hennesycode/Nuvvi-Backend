from django.utils import timezone
from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True)
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    actor_username = serializers.CharField(source="actor.username", read_only=True)
    actor_identification = serializers.CharField(source="actor.identification_number", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    created_at_colombia = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "action", "entity", "entity_id", "status", "status_label", "message", "error_message",
            "request_method", "request_path", "ip_address", "metadata", "created_at", "created_at_colombia",
            "actor", "actor_name", "actor_email", "actor_username", "actor_identification",
        ]

    def get_created_at_colombia(self, obj):
        return timezone.localtime(obj.created_at).strftime("%d/%m/%Y %I:%M:%S %p")
