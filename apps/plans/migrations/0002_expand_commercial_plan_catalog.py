from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="monthly_certificate_fee",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="plan",
            name="short_description",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="plan",
            name="plan_type",
            field=models.CharField(choices=[("invoicing", "Facturación electrónica"), ("payroll_addon", "Complemento de nómina"), ("enterprise", "Empresarial")], default="invoicing", max_length=20),
        ),
        migrations.AddField(
            model_name="plan",
            name="quote_only",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plan",
            name="annual_document_quota",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="plan",
            name="accountant_users",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_branches",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="plan",
            name="max_employees",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="plan",
            name="requires_base_plan",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plan",
            name="certificate_included_annual",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="plan",
            name="support_level",
            field=models.CharField(choices=[("standard", "Estándar"), ("priority", "Prioritario"), ("custom", "Según cotización")], default="standard", max_length=20),
        ),
    ]
