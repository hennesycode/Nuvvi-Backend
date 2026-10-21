from django.db import models
from django.db.models import Q
from django.utils import timezone


class ProviderCapacityPool(models.Model):
    provider = models.CharField(max_length=40, primary_key=True, default="matias")
    documents_purchased = models.PositiveIntegerField(default=5000)
    reserve_documents = models.PositiveIntegerField(default=500)
    review_threshold = models.PositiveIntegerField(default=3500)
    expansion_threshold = models.PositiveIntegerField(default=4000)
    sales_block_threshold = models.PositiveIntegerField(default=4500)
    documents_consumed = models.PositiveIntegerField(default=0)
    provider_period_starts_at = models.DateTimeField(null=True, blank=True)
    provider_period_ends_at = models.DateTimeField(null=True, blank=True)
    capacity_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def sellable_capacity(self):
        return min(self.documents_purchased - self.reserve_documents, self.sales_block_threshold)

    def __str__(self):
        return f"{self.provider}: {self.documents_purchased} documentos"


class SubscriptionModuleBalance(models.Model):
    class Module(models.TextChoices):
        INVOICING = "invoicing", "Facturación"
        PAYROLL = "payroll", "Nómina"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        EXPIRED = "expired", "Vencido"
        CANCELED = "canceled", "Cancelado"

    subscription = models.ForeignKey("subscriptions.Subscription", on_delete=models.PROTECT, related_name="document_balances")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="document_balances")
    company = models.ForeignKey("companies.Company", on_delete=models.SET_NULL, null=True, blank=True, related_name="document_balances")
    company_nit_snapshot = models.CharField(max_length=50)
    module = models.CharField(max_length=12, choices=Module.choices)
    quota = models.PositiveIntegerField()
    committed_documents = models.PositiveIntegerField()
    consumed_documents = models.PositiveIntegerField(default=0)
    period_starts_at = models.DateTimeField()
    period_ends_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["period_ends_at", "module"]
        constraints = [
            models.UniqueConstraint(fields=["subscription", "module", "period_starts_at"], name="billing_unique_subscription_module_period"),
            models.CheckConstraint(condition=Q(consumed_documents__lte=models.F("quota")), name="billing_balance_consumption_lte_quota"),
        ]

    @property
    def remaining_documents(self):
        return self.quota - self.consumed_documents

    def __str__(self):
        return f"{self.company_nit_snapshot} · {self.module} · {self.period_ends_at:%Y-%m-%d}"


class DocumentConsumptionRule(models.Model):
    document_type = models.SlugField(max_length=80, unique=True)
    provider_counts_as_consumption = models.BooleanField(default=False)
    confirmed_with_provider = models.BooleanField(default=False)
    confirmation_notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        state = "confirmada" if self.confirmed_with_provider else "pendiente"
        return f"{self.document_type} · {state}"


class DocumentUsageRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SUCCEEDED = "succeeded", "Contabilizado"
        FAILED = "failed", "Fallido"
        REVERSED = "reversed", "Reversado"

    balance = models.ForeignKey(SubscriptionModuleBalance, on_delete=models.PROTECT, related_name="usage_records")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="document_usage_records")
    company_nit_snapshot = models.CharField(max_length=50)
    document_type = models.SlugField(max_length=80)
    operation_identifier = models.CharField(max_length=160, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    quantity = models.PositiveIntegerField(default=1)
    response_reference = models.CharField(max_length=160, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    counted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class BillingAlert(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Información"
        WARNING = "warning", "Advertencia"
        BLOCK = "block", "Bloqueo preventivo"

    code = models.CharField(max_length=80)
    level = models.CharField(max_length=12, choices=Level.choices)
    message = models.CharField(max_length=255)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="billing_alerts")
    balance = models.ForeignKey(SubscriptionModuleBalance, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts")
    committed_documents = models.PositiveIntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["code", "balance"], condition=Q(balance__isnull=False, resolved_at__isnull=True), name="billing_one_open_balance_alert"),
        ]


class DigitalCertificateRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente de verificación"
        VALID = "valid", "Vigente"
        EXPIRED = "expired", "Vencido"
        REVOKED = "revoked", "Revocado"
        INVALID = "invalid", "No válido"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="digital_certificates")
    company = models.ForeignKey("companies.Company", on_delete=models.SET_NULL, null=True, blank=True, related_name="digital_certificates")
    nit_snapshot = models.CharField(max_length=50)
    issuer = models.CharField(max_length=255)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    issued_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    verification_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["nit_snapshot"], condition=Q(is_current=True), name="billing_one_current_certificate_per_nit"),
        ]

    @property
    def is_valid_for_transmission(self):
        return bool(
            self.status == self.Status.VALID
            and self.issued_at
            and self.expires_at
            and self.issued_at <= timezone.now() < self.expires_at
        )


class DocumentRechargePackage(models.Model):
    code = models.SlugField(max_length=40, unique=True)
    documents = models.PositiveIntegerField()
    price_cop = models.PositiveIntegerField()
    is_available_for_sale = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["documents"]


class DocumentRecharge(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Propuesta"
        PENDING_PAYMENT = "pending_payment", "Pago pendiente"
        ACTIVE = "active", "Activa"
        EXPIRED = "expired", "Vencida"
        CANCELED = "canceled", "Cancelada"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="document_recharges")
    balance = models.ForeignKey(SubscriptionModuleBalance, on_delete=models.PROTECT, related_name="recharges")
    package = models.ForeignKey(DocumentRechargePackage, on_delete=models.PROTECT, related_name="recharges")
    documents = models.PositiveIntegerField()
    price_cop = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)
    period_ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class SubscriptionCertificateCharge(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Propuesta"
        PENDING_PAYMENT = "pending_payment", "Pago pendiente"
        PAID = "paid", "Pagado"
        REFUNDED = "refunded", "Reembolsado"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="certificate_charges")
    certificate = models.ForeignKey(DigitalCertificateRecord, on_delete=models.PROTECT, null=True, blank=True, related_name="charges")
    nit_snapshot = models.CharField(max_length=50)
    amount_cop = models.PositiveIntegerField(default=119000)
    billing_cycle = models.CharField(max_length=10, choices=[("monthly", "Mensual"), ("yearly", "Anual")])
    period_start = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROPOSED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "period_start"], condition=Q(status__in=["proposed", "pending_payment", "paid"]), name="billing_one_certificate_charge_per_nit_cycle"),
        ]
