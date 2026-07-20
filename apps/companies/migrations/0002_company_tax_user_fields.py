from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="company", name="owner_user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_companies", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="company", name="identity_document_id", field=models.CharField(blank=True, default="", max_length=50)),
        migrations.AddField(model_name="company", name="identity_document_code", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="company", name="identity_document_name", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="company", name="verification_digit", field=models.CharField(blank=True, default="", max_length=2)),
        migrations.AddField(model_name="company", name="organization_type_id", field=models.CharField(blank=True, default="", max_length=50)),
        migrations.AddField(model_name="company", name="organization_type_code", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="company", name="organization_type_name", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="company", name="accounting_regime_id", field=models.CharField(blank=True, default="", max_length=50)),
        migrations.AddField(model_name="company", name="accounting_regime_code", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="company", name="accounting_regime_name", field=models.CharField(blank=True, default="", max_length=160)),
        migrations.AddField(model_name="company", name="fiscal_regime_id", field=models.CharField(blank=True, default="", max_length=50)),
        migrations.AddField(model_name="company", name="fiscal_regime_code", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="company", name="fiscal_regime_name", field=models.CharField(blank=True, default="", max_length=160)),
    ]
