from django.conf import settings
from django.db import models


class PlanCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "plan categories"

    def __str__(self):
        return self.name


class Capability(models.Model):
    class ValidationStatus(models.TextChoices):
        PENDING = "pending", "Pendiente de validación"
        AVAILABLE = "available", "Disponible y validada"
        UNAVAILABLE = "unavailable", "No disponible"

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    description = models.CharField(max_length=255, blank=True, default="")
    validation_status = models.CharField(max_length=16, choices=ValidationStatus.choices, default=ValidationStatus.PENDING)
    validation_notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_plan_capabilities")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Plan(models.Model):
    class CatalogStatus(models.TextChoices):
        DRAFT = "draft", "Borrador"
        PUBLISHED = "published", "Publicado"
        RETIRED = "retired", "Retirado"
        ARCHIVED = "archived", "Archivado"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Público"
        PRIVATE = "private", "Privado"
        LINK = "link", "Disponible mediante enlace"
        QUOTE = "quote", "Solo cotización"

    class PlanType(models.TextChoices):
        INVOICING = "invoicing", "Facturación electrónica"
        PAYROLL_ADDON = "payroll_addon", "Complemento de nómina"
        ENTERPRISE = "enterprise", "Empresarial"

    class SupportLevel(models.TextChoices):
        STANDARD = "standard", "Estándar"
        PRIORITY = "priority", "Prioritario"
        CUSTOM = "custom", "Según cotización"

    class CommercialStatus(models.TextChoices):
        LEGACY = "legacy", "Oferta anterior"
        PROPOSAL = "proposal", "Propuesta"
        APPROVED = "approved", "Aprobada"

    class TaxValidationStatus(models.TextChoices):
        UNKNOWN = "unknown", "Sin validar"
        PENDING = "pending", "Pendiente de contador"
        VALIDATED = "validated", "Validación tributaria aprobada"

    code = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    short_description = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    target_audience = models.CharField(max_length=255, blank=True, default="")
    commercial_badge = models.CharField(max_length=80, blank=True, default="")
    display_order = models.PositiveIntegerField(default=0)
    catalog_status = models.CharField(max_length=12, choices=CatalogStatus.choices, default=CatalogStatus.DRAFT)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    plan_type = models.CharField(max_length=20, choices=PlanType.choices, default=PlanType.INVOICING)
    category = models.ForeignKey(PlanCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="plans")
    features = models.JSONField(default=list, blank=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, default=None)
    yearly_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, default=None)
    monthly_certificate_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quote_only = models.BooleanField(default=False)
    annual_document_quota = models.PositiveIntegerField(default=0, blank=True, null=True)
    max_users = models.PositiveIntegerField(default=1, blank=True, null=True)
    accountant_users = models.PositiveIntegerField(default=0, blank=True, null=True)
    max_issuers = models.PositiveIntegerField(default=1)
    max_branches = models.PositiveIntegerField(default=1, blank=True, null=True)
    max_documents_per_month = models.PositiveIntegerField(default=0, blank=True, null=True)
    max_employees = models.PositiveIntegerField(default=0, blank=True, null=True)
    requires_base_plan = models.BooleanField(default=False)
    certificate_included_annual = models.BooleanField(default=False)
    support_level = models.CharField(max_length=20, choices=SupportLevel.choices, default=SupportLevel.STANDARD)
    has_inventory = models.BooleanField(default=False)
    has_cash_register = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    commercial_status = models.CharField(max_length=12, choices=CommercialStatus.choices, default=CommercialStatus.LEGACY)
    tax_validation_status = models.CharField(max_length=12, choices=TaxValidationStatus.choices, default=TaxValidationStatus.UNKNOWN)
    tax_validation_note = models.TextField(blank=True, default="")
    quotation_scope = models.JSONField(default=dict, blank=True)
    capabilities = models.ManyToManyField(Capability, through="PlanCapability", related_name="plans", blank=True)
    parent_plan = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="versions")
    version_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plans_plan"
        ordering = ["display_order", "monthly_price", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["parent_plan", "version_number"],
                condition=models.Q(parent_plan__isnull=False),
                name="plans_unique_child_version",
            ),
        ]

    def __str__(self):
        return self.name


class PlanCapability(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_capabilities")
    capability = models.ForeignKey(Capability, on_delete=models.PROTECT, related_name="plan_assignments")
    scope_level = models.CharField(max_length=40, blank=True, default="")
    included_in_proposal = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["plan", "capability"], name="plans_unique_plan_capability")]
        ordering = ["capability__name"]


class PlanBundle(models.Model):
    class CommercialStatus(models.TextChoices):
        PROPOSAL = "proposal", "Propuesta"
        APPROVED = "approved", "Aprobada"

    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=160)
    short_description = models.CharField(max_length=255, blank=True, default="")
    billing_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="billing_bundles")
    payroll_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="payroll_bundles")
    display_order = models.PositiveIntegerField(default=0)
    commercial_status = models.CharField(max_length=12, choices=CommercialStatus.choices, default=CommercialStatus.PROPOSAL)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]

    @property
    def monthly_price(self):
        return (self.billing_plan.monthly_price or 0) + (self.payroll_plan.monthly_price or 0)

    @property
    def yearly_price(self):
        return (self.billing_plan.yearly_price or 0) + (self.payroll_plan.yearly_price or 0)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.billing_plan_id and self.billing_plan.plan_type != Plan.PlanType.INVOICING:
            raise ValidationError({"billing_plan": "El componente principal debe ser un plan de facturación."})
        if self.payroll_plan_id and self.payroll_plan.plan_type != Plan.PlanType.PAYROLL_ADDON:
            raise ValidationError({"payroll_plan": "El complemento debe ser un plan de nómina."})

    def __str__(self):
        return self.name
