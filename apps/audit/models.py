from django.db import models


class AuditLog(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_WARNING = "warning"

    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Exitoso"),
        (STATUS_ERROR, "Error"),
        (STATUS_WARNING, "Advertencia"),
    ]

    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="audit_logs", null=True, blank=True)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="audit_logs", null=True, blank=True)
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    message = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    request_method = models.CharField(max_length=12, blank=True)
    request_path = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["entity", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity}#{self.entity_id}"
