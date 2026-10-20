from django.db import migrations, models


def update_catalog_counts(apps, schema_editor):
    MatiasConnection = apps.get_model("dian", "MatiasConnection")
    MatiasCatalogSync = apps.get_model("dian", "MatiasCatalogSync")
    MatiasConnection.objects.all().update(catalogs_total_count=20)
    # Older versions tracked only record counts, not the records themselves.
    # Force a fresh sync rather than presenting those counts as usable data.
    MatiasConnection.objects.all().update(
        catalogs_status="pending", catalogs_synced_count=0, catalogs_detail=[]
    )
    MatiasCatalogSync.objects.all().update(
        status="pending",
        catalog_data=[],
        records_count=None,
        last_attempt_at=None,
        last_success_at=None,
        error_message="",
    )
    MatiasConnection.objects.all().update(catalogs_last_synced_at=None)


class Migration(migrations.Migration):

    dependencies = [("dian", "0006_matias_pat_endpoint_tokens")]

    operations = [
        migrations.AddField(
            model_name="matiascatalogsync",
            name="catalog_data",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="matiasconnection",
            name="catalogs_total_count",
            field=models.PositiveSmallIntegerField(default=20),
        ),
        migrations.RunPython(update_catalog_counts, migrations.RunPython.noop),
    ]
