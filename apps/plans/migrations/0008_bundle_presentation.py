from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("plans", "0007_planbundle_discount_percent")]
    operations = [
        migrations.AddField(model_name="planbundle", name="quote_only", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="planbundle", name="features", field=models.JSONField(default=None, null=True, blank=True)),
    ]
