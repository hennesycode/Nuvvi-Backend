from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "admin_role", "is_active", "is_staff", "is_superuser", "created_at")
    list_filter = ("admin_role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "full_name", "identification_number")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "first_name", "last_name", "admin_role", "identification_type", "identification_number", "country", "department", "city", "address", "phone_country_code", "phone_number")}),
        ("Invitation", {"fields": ("password_setup_expires_at", "password_setup_used_at", "invitation_sent_at")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "password_setup_expires_at", "password_setup_used_at", "invitation_sent_at")
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2"),
        }),
    )
