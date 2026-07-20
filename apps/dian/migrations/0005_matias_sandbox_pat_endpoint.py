from django.db import migrations, models


def set_sandbox_endpoint(apps, schema_editor):
    MatiasConnection = apps.get_model("dian", "MatiasConnection")
    MatiasConnection.objects.filter(environment="sandbox").update(token_generation_endpoint="/auth/token")


class Migration(migrations.Migration):

    dependencies = [
        ("dian", "0004_matias_environment_flow"),
    ]

    operations = [
        migrations.AlterField(
            model_name="matiasconnection",
            name="token_generation_endpoint",
            field=models.CharField(default="/auth/token", max_length=80),
        ),
        migrations.RunPython(set_sandbox_endpoint, migrations.RunPython.noop),
    ]
