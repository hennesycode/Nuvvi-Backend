from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "status", "billing_cycle", "current_period_start", "current_period_end")
    list_filter = ("status", "billing_cycle", "plan")
    search_fields = ("tenant__name", "plan__name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
