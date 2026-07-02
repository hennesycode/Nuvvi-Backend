from django.db import models


class DianEnvironment(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "dian_environment"
        ordering = ["name"]

    def __str__(self):
        return self.name


class IssuerCompany(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="issuers")
    legal_name = models.CharField(max_length=255)
    nit = models.CharField(max_length=50)
    dv = models.CharField(max_length=5, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    dian_environment = models.ForeignKey(DianEnvironment, on_delete=models.PROTECT, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dian_issuer_company"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.legal_name} ({self.nit})"


class DianDocumentLog(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="dian_logs")
    issuer_company = models.ForeignKey(IssuerCompany, on_delete=models.PROTECT, related_name="document_logs")
    document_type = models.CharField(max_length=50)
    external_id = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="pending")
    provider_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dian_document_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document_type} — {self.external_id} ({self.status})"
