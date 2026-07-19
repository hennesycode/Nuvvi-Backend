import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dian", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MatiasConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="MATIAS API", max_length=120)),
                ("environment", models.CharField(choices=[("sandbox", "Sandbox"), ("production", "Producción")], default="sandbox", max_length=20)),
                ("base_url", models.URLField(default="https://sandbox-api.matias-api.com/api/ubl2.1", max_length=255)),
                ("enabled", models.BooleanField(default=False)),
                ("timeout_seconds", models.PositiveSmallIntegerField(default=20)),
                ("retry_attempts", models.PositiveSmallIntegerField(default=2)),
                ("auth_method", models.CharField(default="PAT", max_length=20)),
                ("encrypted_access_token", models.TextField(blank=True)),
                ("token_external_id", models.CharField(blank=True, max_length=120)),
                ("token_name", models.CharField(blank=True, max_length=120)),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("account_email", models.EmailField(blank=True, max_length=254)),
                ("parent_company_uuid", models.CharField(blank=True, max_length=120)),
                ("external_company_id", models.CharField(blank=True, max_length=120)),
                ("external_company_name", models.CharField(blank=True, max_length=255)),
                ("external_company_nit", models.CharField(blank=True, max_length=50)),
                ("account_main_email", models.EmailField(blank=True, max_length=254)),
                ("linked_companies_count", models.PositiveIntegerField(default=0)),
                ("connection_status", models.CharField(default="DISCONNECTED", max_length=40)),
                ("operational_status", models.CharField(default="CATALOGS_NOT_SYNCHRONIZED", max_length=50)),
                ("environment_detected", models.CharField(blank=True, max_length=30)),
                ("multicompany_verified", models.BooleanField(default=False)),
                ("last_test_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_code", models.CharField(blank=True, max_length=50)),
                ("last_error_message", models.TextField(blank=True)),
                ("last_response_time_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("last_test_results", models.JSONField(blank=True, default=list)),
                ("catalogs_status", models.CharField(default="pending", max_length=20)),
                ("catalogs_synced_count", models.PositiveSmallIntegerField(default=0)),
                ("catalogs_total_count", models.PositiveSmallIntegerField(default=17)),
                ("catalogs_last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("catalogs_detail", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="matias_connections_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="matias_connections_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "matias_connections", "ordering": ["-created_at"]},
        ),
    ]
