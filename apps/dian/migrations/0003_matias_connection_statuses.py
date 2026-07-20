from django.db import migrations, models


def update_existing_connections(apps, schema_editor):
    MatiasConnection = apps.get_model("dian", "MatiasConnection")
    for connection in MatiasConnection.objects.all():
        changed = False
        if not connection.enabled:
            connection.connection_status = "DISABLED"
            connection.operational_status = "INACTIVE"
            changed = True
        elif not connection.encrypted_access_token:
            connection.connection_status = "NOT_CONFIGURED"
            connection.operational_status = "PAT_REQUIRED"
            changed = True
        if connection.catalogs_total_count != 18:
            connection.catalogs_total_count = 18
            changed = True
        if changed:
            connection.save(update_fields=["connection_status", "operational_status", "catalogs_total_count"])


class Migration(migrations.Migration):

    dependencies = [
        ("dian", "0002_matias_connection"),
    ]

    operations = [
        migrations.AddField(
            model_name="matiasconnection",
            name="token_generation_endpoint",
            field=models.CharField(default="/tokens", max_length=80),
        ),
        migrations.AlterField(
            model_name="matiasconnection",
            name="catalogs_total_count",
            field=models.PositiveSmallIntegerField(default=18),
        ),
        migrations.AlterField(
            model_name="matiasconnection",
            name="connection_status",
            field=models.CharField(default="DISABLED", max_length=40),
        ),
        migrations.AlterField(
            model_name="matiasconnection",
            name="operational_status",
            field=models.CharField(default="INACTIVE", max_length=50),
        ),
        migrations.RunPython(update_existing_connections, migrations.RunPython.noop),
    ]
