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

    code = models.CharField(max_length=50, unique=True)
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
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    yearly_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_certificate_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quote_only = models.BooleanField(default=False)
    annual_document_quota = models.PositiveIntegerField(default=0)
    max_users = models.PositiveIntegerField(default=1)
    accountant_users = models.PositiveIntegerField(default=0)
    max_issuers = models.PositiveIntegerField(default=1)
    max_branches = models.PositiveIntegerField(default=1)
    max_documents_per_month = models.PositiveIntegerField(default=0)
    max_employees = models.PositiveIntegerField(default=0)
    requires_base_plan = models.BooleanField(default=False)
    certificate_included_annual = models.BooleanField(default=False)
    support_level = models.CharField(max_length=20, choices=SupportLevel.choices, default=SupportLevel.STANDARD)
    has_inventory = models.BooleanField(default=False)
    has_cash_register = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plans_plan"
        ordering = ["display_order", "monthly_price", "id"]

    def __str__(self):
        return self.name
