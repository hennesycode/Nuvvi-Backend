from django.db import migrations, models
import django.db.models.deletion


def prepare_environment_records(apps, schema_editor):
    MatiasConnection = apps.get_model("dian", "MatiasConnection")
    sandbox = MatiasConnection.objects.filter(environment="sandbox").order_by("id").first()
    if sandbox:
        sandbox.name = "MATIAS_SANDBOX"
        sandbox.environment = "sandbox"
        sandbox.catalogs_total_count = 18
        sandbox.save(update_fields=["name", "environment", "catalogs_total_count"])
    production = MatiasConnection.objects.filter(environment="production").order_by("id").first()
    if production:
        production.name = "MATIAS_PRODUCTION"
        production.catalogs_total_count = 18
        production.save(update_fields=["name", "catalogs_total_count"])


class Migration(migrations.Migration):

    dependencies = [
        ("dian", "0003_matias_connection_statuses"),
    ]

    operations = [
        migrations.AddField(
            model_name="matiasconnection",
            name="authenticated_user_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="authenticated_user_id",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="catalogs_last_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="external_company_status",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_company_limit",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_documents_available",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_documents_consumed",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_plan",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_status",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="membership_summary",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="matiasconnection",
            name="token_created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(prepare_environment_records, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="matiasconnection",
            constraint=models.UniqueConstraint(fields=("environment",), name="unique_matias_connection_environment"),
        ),
        migrations.CreateModel(
            name="MatiasCatalogSync",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("catalog_name", models.CharField(max_length=120)),
                ("endpoint", models.CharField(max_length=120)),
                ("status", models.CharField(default="pending", max_length=20)),
                ("records_count", models.PositiveIntegerField(blank=True, null=True)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("http_status", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("response_time_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("connection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="catalog_syncs", to="dian.matiasconnection")),
            ],
            options={
                "db_table": "matias_catalog_syncs",
                "ordering": ["endpoint"],
                "unique_together": {("connection", "endpoint")},
            },
        ),
    ]
