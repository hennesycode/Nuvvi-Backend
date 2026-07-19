from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_SUPERADMIN = "superadmin"
    ROLE_FINANCE = "finance"
    ROLE_SUPPORT = "support"

    ADMIN_ROLE_CHOICES = [
        (ROLE_SUPERADMIN, "Superadministrador"),
        (ROLE_FINANCE, "Finanzas y cartera"),
        (ROLE_SUPPORT, "Soporte"),
    ]

    IDENTIFICATION_CC = "cc"
    IDENTIFICATION_CE = "ce"
    IDENTIFICATION_NIT = "nit"
    IDENTIFICATION_PASSPORT = "passport"

    IDENTIFICATION_TYPE_CHOICES = [
        (IDENTIFICATION_CC, "Cédula de ciudadanía"),
        (IDENTIFICATION_CE, "Cédula de extranjería"),
        (IDENTIFICATION_NIT, "NIT"),
        (IDENTIFICATION_PASSPORT, "Pasaporte"),
    ]

    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    admin_role = models.CharField(max_length=30, choices=ADMIN_ROLE_CHOICES, blank=True)
    identification_type = models.CharField(max_length=20, choices=IDENTIFICATION_TYPE_CHOICES, blank=True)
    identification_number = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=80, default="Colombia")
    department = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone_country_code = models.CharField(max_length=8, default="+57")
    phone_number = models.CharField(max_length=10, blank=True)
    password_setup_token_hash = models.CharField(max_length=64, blank=True)
    password_setup_expires_at = models.DateTimeField(null=True, blank=True)
    password_setup_used_at = models.DateTimeField(null=True, blank=True)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
