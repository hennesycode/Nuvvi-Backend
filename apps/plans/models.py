from django.db import models


class PlanCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "plan categories"

    def __str__(self):
        return self.name


class Plan(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(PlanCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="plans")
    features = models.JSONField(default=list, blank=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    yearly_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=1)
    max_issuers = models.PositiveIntegerField(default=1)
    max_documents_per_month = models.PositiveIntegerField(default=0)
    has_inventory = models.BooleanField(default=False)
    has_cash_register = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plans_plan"
        ordering = ["monthly_price"]

    def __str__(self):
        return self.name
