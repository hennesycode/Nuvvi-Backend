from django.db import migrations, models


def set_tokens_endpoint(apps, schema_editor):
    MatiasConnection = apps.get_model("dian", "MatiasConnection")
    MatiasConnection.objects.filter(environment="sandbox").update(token_generation_endpoint="/tokens")


class Migration(migrations.Migration):

    dependencies = [
        ("dian", "0005_matias_sandbox_pat_endpoint"),
    ]

    operations = [
        migrations.AlterField(
            model_name="matiasconnection",
            name="token_generation_endpoint",
            field=models.CharField(default="/tokens", max_length=80),
        ),
        migrations.RunPython(set_tokens_endpoint, migrations.RunPython.noop),
    ]
