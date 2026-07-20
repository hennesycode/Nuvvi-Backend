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


class MatiasConnection(models.Model):
    ENVIRONMENT_SANDBOX = "sandbox"
    ENVIRONMENT_PRODUCTION = "production"
    ENVIRONMENT_CHOICES = [
        (ENVIRONMENT_SANDBOX, "Sandbox"),
        (ENVIRONMENT_PRODUCTION, "Producción"),
    ]

    STATUS_CONNECTED = "CONNECTED"
    STATUS_DISCONNECTED = "DISCONNECTED"
    STATUS_DISABLED = "DISABLED"
    STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
    STATUS_TESTING = "TESTING"
    STATUS_AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    STATUS_API_UNAVAILABLE = "API_UNAVAILABLE"
    STATUS_TIMEOUT = "TIMEOUT"
    STATUS_ENVIRONMENT_MISMATCH = "ENVIRONMENT_MISMATCH"
    STATUS_CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

    OP_INACTIVE = "INACTIVE"
    OP_PAT_REQUIRED = "PAT_REQUIRED"
    OP_PAT_ENDPOINT_NOT_FOUND = "PAT_ENDPOINT_NOT_FOUND"
    OP_PAT_VALIDATION_ERROR = "PAT_VALIDATION_ERROR"
    OP_PAT_VALID = "PAT_VALID"
    OP_ACCOUNT_NOT_DETECTED = "ACCOUNT_NOT_DETECTED"
    OP_PARENT_UUID_REQUIRED = "PARENT_UUID_REQUIRED"
    OP_MULTICOMPANY_PENDING = "MULTICOMPANY_PENDING"
    OP_MULTICOMPANY_VERIFIED = "MULTICOMPANY_VERIFIED"
    OP_MEMBERSHIP_INACTIVE = "MEMBERSHIP_INACTIVE"
    OP_CATALOGS_PENDING = "CATALOGS_PENDING"
    OP_CATALOGS_PARTIAL = "CATALOGS_PARTIAL"
    OP_READY = "READY_TO_REGISTER_COMPANIES"
    OP_PARENT_NOT_FOUND = "PARENT_COMPANY_NOT_FOUND"
    OP_MULTICOMPANY_DENIED = "MULTICOMPANY_PERMISSION_DENIED"
    OP_TOKEN_EXPIRED = "TOKEN_EXPIRED"
    OP_CATALOGS_NOT_SYNCED = "CATALOGS_NOT_SYNCHRONIZED"

    CATALOGS_PENDING = "pending"
    CATALOGS_SYNCED = "synced"
    CATALOGS_PARTIAL = "partial"
    CATALOGS_ERROR = "error"

    name = models.CharField(max_length=120, default="MATIAS API")
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default=ENVIRONMENT_SANDBOX)
    base_url = models.URLField(max_length=255, default="https://sandbox-api.matias-api.com/api/ubl2.1")
    enabled = models.BooleanField(default=False)
    timeout_seconds = models.PositiveSmallIntegerField(default=20)
    retry_attempts = models.PositiveSmallIntegerField(default=2)
    token_generation_endpoint = models.CharField(max_length=80, default="/tokens")

    auth_method = models.CharField(max_length=20, default="PAT")
    encrypted_access_token = models.TextField(blank=True)
    token_external_id = models.CharField(max_length=120, blank=True)
    token_name = models.CharField(max_length=120, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    token_created_at = models.DateTimeField(null=True, blank=True)
    authenticated_user_id = models.CharField(max_length=120, blank=True)
    authenticated_user_email = models.EmailField(blank=True)
    account_email = models.EmailField(blank=True)

    parent_company_uuid = models.CharField(max_length=120, blank=True)
    external_company_id = models.CharField(max_length=120, blank=True)
    external_company_name = models.CharField(max_length=255, blank=True)
    external_company_nit = models.CharField(max_length=50, blank=True)
    account_main_email = models.EmailField(blank=True)
    linked_companies_count = models.PositiveIntegerField(default=0)
    external_company_status = models.CharField(max_length=80, blank=True)
    membership_plan = models.CharField(max_length=120, blank=True)
    membership_status = models.CharField(max_length=80, blank=True)
    membership_expires_at = models.DateTimeField(null=True, blank=True)
    membership_documents_available = models.PositiveIntegerField(null=True, blank=True)
    membership_documents_consumed = models.PositiveIntegerField(null=True, blank=True)
    membership_company_limit = models.PositiveIntegerField(null=True, blank=True)
    membership_summary = models.JSONField(default=dict, blank=True)

    connection_status = models.CharField(max_length=40, default=STATUS_DISABLED)
    operational_status = models.CharField(max_length=50, default=OP_INACTIVE)
    environment_detected = models.CharField(max_length=30, blank=True)
    multicompany_verified = models.BooleanField(default=False)

    last_test_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=50, blank=True)
    last_error_message = models.TextField(blank=True)
    last_response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    last_test_results = models.JSONField(default=list, blank=True)

    catalogs_status = models.CharField(max_length=20, default=CATALOGS_PENDING)
    catalogs_synced_count = models.PositiveSmallIntegerField(default=0)
    catalogs_total_count = models.PositiveSmallIntegerField(default=18)
    catalogs_last_attempt_at = models.DateTimeField(null=True, blank=True)
    catalogs_last_synced_at = models.DateTimeField(null=True, blank=True)
    catalogs_detail = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="matias_connections_created", null=True, blank=True)
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="matias_connections_updated", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "matias_connections"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["environment"], name="unique_matias_connection_environment")]

    def __str__(self):
        return f"{self.name} ({self.environment})"


class MatiasCatalogSync(models.Model):
    connection = models.ForeignKey(MatiasConnection, on_delete=models.CASCADE, related_name="catalog_syncs")
    catalog_name = models.CharField(max_length=120)
    endpoint = models.CharField(max_length=120)
    status = models.CharField(max_length=20, default=MatiasConnection.CATALOGS_PENDING)
    records_count = models.PositiveIntegerField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "matias_catalog_syncs"
        unique_together = ["connection", "endpoint"]
        ordering = ["endpoint"]

    def __str__(self):
        return f"{self.catalog_name} ({self.connection.environment})"
