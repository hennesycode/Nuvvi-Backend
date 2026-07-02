from django.contrib import admin
from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "monthly_price", "yearly_price", "max_users", "has_api_access", "is_active")
    list_filter = ("is_active", "has_inventory", "has_cash_register", "has_api_access")
    search_fields = ("code", "name")
    ordering = ("monthly_price",)
    readonly_fields = ("created_at", "updated_at")
