from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="audit_logs", null=True, blank=True)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="audit_logs", null=True, blank=True)
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.entity}#{self.entity_id}"
