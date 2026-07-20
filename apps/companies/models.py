import uuid

from django.db import models


class Company(models.Model):
    LOCAL_DRAFT = "DRAFT"
    LOCAL_ACTIVE = "ACTIVE"
    LOCAL_SUSPENDED = "SUSPENDED"
    LOCAL_ARCHIVED = "ARCHIVED"
    LOCAL_STATUS_CHOICES = [
        (LOCAL_DRAFT, "Borrador"),
        (LOCAL_ACTIVE, "Activa"),
        (LOCAL_SUSPENDED, "Suspendida"),
        (LOCAL_ARCHIVED, "Archivada"),
    ]

    ONBOARDING_COMPANY_REGISTERED = "COMPANY_REGISTERED"
    ONBOARDING_TAX_INFORMATION_PENDING = "TAX_INFORMATION_PENDING"
    ONBOARDING_DIAN_SOFTWARE_PENDING = "DIAN_SOFTWARE_PENDING"
    ONBOARDING_RESOLUTION_PENDING = "RESOLUTION_PENDING"
    ONBOARDING_CERTIFICATE_PENDING = "CERTIFICATE_PENDING"
    ONBOARDING_READY_TO_INVOICE = "READY_TO_INVOICE"
    ONBOARDING_CHOICES = [
        (ONBOARDING_COMPANY_REGISTERED, "Empresa registrada"),
        (ONBOARDING_TAX_INFORMATION_PENDING, "Datos tributarios pendientes"),
        (ONBOARDING_DIAN_SOFTWARE_PENDING, "Software DIAN pendiente"),
        (ONBOARDING_RESOLUTION_PENDING, "Resolución pendiente"),
        (ONBOARDING_CERTIFICATE_PENDING, "Certificado pendiente"),
        (ONBOARDING_READY_TO_INVOICE, "Lista para facturar"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    environment = models.CharField(max_length=20, default="sandbox")
    legal_name = models.CharField(max_length=255)
    nit = models.CharField(max_length=50, db_index=True)
    email = models.EmailField(db_index=True)
    owner_first_name = models.CharField(max_length=120)
    owner_last_name = models.CharField(max_length=120)
    owner_user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="owned_companies", null=True, blank=True)
    identity_document_id = models.CharField(max_length=50, blank=True, default="")
    identity_document_code = models.CharField(max_length=20, blank=True, default="")
    identity_document_name = models.CharField(max_length=120, blank=True, default="")
    verification_digit = models.CharField(max_length=2, blank=True, default="")
    organization_type_id = models.CharField(max_length=50, blank=True, default="")
    organization_type_code = models.CharField(max_length=20, blank=True, default="")
    organization_type_name = models.CharField(max_length=120, blank=True, default="")
    accounting_regime_id = models.CharField(max_length=50, blank=True, default="")
    accounting_regime_code = models.CharField(max_length=20, blank=True, default="")
    accounting_regime_name = models.CharField(max_length=160, blank=True, default="")
    fiscal_regime_id = models.CharField(max_length=50, blank=True, default="")
    fiscal_regime_code = models.CharField(max_length=20, blank=True, default="")
    fiscal_regime_name = models.CharField(max_length=160, blank=True, default="")
    country_id = models.CharField(max_length=50)
    department_id = models.CharField(max_length=50, blank=True, default="")
    city_id = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    mobile = models.CharField(max_length=50)
    phone = models.CharField(max_length=50, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    assigned_executive = models.CharField(max_length=120, blank=True, default="")
    local_status = models.CharField(max_length=20, choices=LOCAL_STATUS_CHOICES, default=LOCAL_ACTIVE)
    onboarding_status = models.CharField(max_length=40, choices=ONBOARDING_CHOICES, default=ONBOARDING_COMPANY_REGISTERED)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="companies_created", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "companies"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["environment", "nit"], name="companies_env_nit_idx"),
            models.Index(fields=["environment", "email"], name="companies_env_email_idx"),
            models.Index(fields=["nit", "archived_at"], name="companies_nit_archived_idx"),
            models.Index(fields=["email", "archived_at"], name="companies_email_archived_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["environment", "nit"], name="unique_company_nit_per_environment"),
            models.UniqueConstraint(fields=["environment", "email"], name="unique_company_email_per_environment"),
        ]

    def __str__(self):
        return f"{self.legal_name} ({self.nit})"


class CompanyProviderLink(models.Model):
    PROVIDER_MATIAS = "MATIAS"
    ENVIRONMENT_SANDBOX = "sandbox"
    ENVIRONMENT_PRODUCTION = "production"

    STATUS_NOT_REGISTERED = "NOT_REGISTERED"
    STATUS_PENDING_CREATION = "PENDING_CREATION"
    STATUS_REGISTERED = "REGISTERED"
    STATUS_PENDING_UPDATE = "PENDING_UPDATE"
    STATUS_SYNC_ERROR = "SYNC_ERROR"
    STATUS_REMOTE_CREATED_IDENTIFIERS_PENDING = "REMOTE_CREATED_IDENTIFIERS_PENDING"
    STATUS_REMOTE_DISABLED = "REMOTE_DISABLED"
    STATUS_DELETION_PENDING = "DELETION_PENDING"
    STATUS_REMOTE_NOT_FOUND = "REMOTE_NOT_FOUND"
    STATUS_CHOICES = [
        (STATUS_NOT_REGISTERED, "No registrada"),
        (STATUS_PENDING_CREATION, "Creación pendiente"),
        (STATUS_REGISTERED, "Registrada"),
        (STATUS_PENDING_UPDATE, "Actualización pendiente"),
        (STATUS_SYNC_ERROR, "Error de sincronización"),
        (STATUS_REMOTE_CREATED_IDENTIFIERS_PENDING, "Identificadores MATIAS pendientes"),
        (STATUS_REMOTE_DISABLED, "Desactivada en proveedor"),
        (STATUS_DELETION_PENDING, "Desactivación pendiente"),
        (STATUS_REMOTE_NOT_FOUND, "No encontrada en proveedor"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="provider_links")
    provider = models.CharField(max_length=30, default=PROVIDER_MATIAS)
    environment = models.CharField(max_length=20, default=ENVIRONMENT_SANDBOX)
    parent_company_uuid = models.CharField(max_length=120, blank=True, default="")
    matias_company_id = models.CharField(max_length=120, blank=True, default="")
    matias_client_uuid = models.CharField(max_length=120, blank=True, default="")
    remote_name = models.CharField(max_length=255, blank=True, default="")
    remote_nit = models.CharField(max_length=50, blank=True, default="")
    remote_email = models.EmailField(blank=True, default="")
    provider_status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_NOT_REGISTERED)
    enabled_in_provider = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=50, blank=True, default="")
    last_error_message = models.TextField(blank=True, default="")
    last_remote_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_provider_links"
        constraints = [models.UniqueConstraint(fields=["company", "provider", "environment"], name="unique_company_provider_environment")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.provider} {self.environment} - {self.company_id}"


class CompanySyncAttempt(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sync_attempts", null=True, blank=True)
    operation = models.CharField(max_length=40)
    request_identifier = models.CharField(max_length=80, unique=True, null=True, blank=True)
    http_method = models.CharField(max_length=10, blank=True, default="")
    endpoint = models.CharField(max_length=255, blank=True, default="")
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    successful = models.BooleanField(default=False)
    error_code = models.CharField(max_length=50, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="company_sync_attempts", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "company_sync_attempts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.operation} {self.http_status or '-'}"
