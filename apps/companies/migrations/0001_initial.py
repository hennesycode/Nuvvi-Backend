# Generated manually for the Empresas module.

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("legal_name", models.CharField(max_length=255)),
                ("nit", models.CharField(db_index=True, max_length=50)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("owner_first_name", models.CharField(max_length=120)),
                ("owner_last_name", models.CharField(max_length=120)),
                ("country_id", models.CharField(max_length=50)),
                ("department_id", models.CharField(blank=True, default="", max_length=50)),
                ("city_id", models.CharField(max_length=50)),
                ("address", models.CharField(max_length=255)),
                ("mobile", models.CharField(max_length=50)),
                ("phone", models.CharField(blank=True, default="", max_length=50)),
                ("notes", models.TextField(blank=True, default="")),
                ("assigned_executive", models.CharField(blank=True, default="", max_length=120)),
                ("local_status", models.CharField(choices=[("DRAFT", "Borrador"), ("ACTIVE", "Activa"), ("SUSPENDED", "Suspendida"), ("ARCHIVED", "Archivada")], default="ACTIVE", max_length=20)),
                ("onboarding_status", models.CharField(choices=[("COMPANY_REGISTERED", "Empresa registrada"), ("TAX_INFORMATION_PENDING", "Datos tributarios pendientes"), ("DIAN_SOFTWARE_PENDING", "Software DIAN pendiente"), ("RESOLUTION_PENDING", "Resolución pendiente"), ("CERTIFICATE_PENDING", "Certificado pendiente"), ("READY_TO_INVOICE", "Lista para facturar")], default="COMPANY_REGISTERED", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="companies_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "companies", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CompanyProviderLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="MATIAS", max_length=30)),
                ("environment", models.CharField(default="sandbox", max_length=20)),
                ("parent_company_uuid", models.CharField(blank=True, default="", max_length=120)),
                ("matias_company_id", models.CharField(blank=True, default="", max_length=120)),
                ("matias_client_uuid", models.CharField(blank=True, default="", max_length=120)),
                ("remote_name", models.CharField(blank=True, default="", max_length=255)),
                ("remote_nit", models.CharField(blank=True, default="", max_length=50)),
                ("remote_email", models.EmailField(blank=True, default="", max_length=254)),
                ("provider_status", models.CharField(choices=[("NOT_REGISTERED", "No registrada"), ("PENDING_CREATION", "Creación pendiente"), ("REGISTERED", "Registrada"), ("PENDING_UPDATE", "Actualización pendiente"), ("SYNC_ERROR", "Error de sincronización"), ("REMOTE_DISABLED", "Desactivada en proveedor"), ("DELETION_PENDING", "Desactivación pendiente"), ("REMOTE_NOT_FOUND", "No encontrada en proveedor")], default="NOT_REGISTERED", max_length=40)),
                ("enabled_in_provider", models.BooleanField(default=False)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_code", models.CharField(blank=True, default="", max_length=50)),
                ("last_error_message", models.TextField(blank=True, default="")),
                ("last_remote_snapshot", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="provider_links", to="companies.company")),
            ],
            options={"db_table": "company_provider_links", "ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="CompanySyncAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(max_length=40)),
                ("request_identifier", models.CharField(blank=True, max_length=80, null=True, unique=True)),
                ("http_method", models.CharField(blank=True, default="", max_length=10)),
                ("endpoint", models.CharField(blank=True, default="", max_length=255)),
                ("http_status", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("successful", models.BooleanField(default=False)),
                ("error_code", models.CharField(blank=True, default="", max_length=50)),
                ("error_message", models.TextField(blank=True, default="")),
                ("response_time_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="sync_attempts", to="companies.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="company_sync_attempts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "company_sync_attempts", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="company", index=models.Index(fields=["nit", "archived_at"], name="companies_nit_archived_idx")),
        migrations.AddIndex(model_name="company", index=models.Index(fields=["email", "archived_at"], name="companies_email_archived_idx")),
        migrations.AddConstraint(model_name="companyproviderlink", constraint=models.UniqueConstraint(fields=("company", "provider", "environment"), name="unique_company_provider_environment")),
    ]
