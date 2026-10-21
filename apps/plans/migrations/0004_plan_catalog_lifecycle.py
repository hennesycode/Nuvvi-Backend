from django.db import migrations, models


def mark_existing_plans_published(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Plan.objects.filter(is_active=True).update(catalog_status="published", visibility="public")
    Plan.objects.filter(is_active=False).update(catalog_status="retired", visibility="private")


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0003_merge_plan_migrations"),
    ]

    operations = [
        migrations.AddField(
            model_name="plancategory",
            name="display_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="plancategory",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="plan",
            name="target_audience",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="plan",
            name="commercial_badge",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="plan",
            name="display_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="plan",
            name="catalog_status",
            field=models.CharField(choices=[("draft", "Borrador"), ("published", "Publicado"), ("retired", "Retirado"), ("archived", "Archivado")], default="draft", max_length=12),
        ),
        migrations.AddField(
            model_name="plan",
            name="visibility",
            field=models.CharField(choices=[("public", "Público"), ("private", "Privado"), ("link", "Disponible mediante enlace"), ("quote", "Solo cotización")], default="private", max_length=10),
        ),
        migrations.RunPython(mark_existing_plans_published, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="plancategory",
            options={"ordering": ["display_order", "name"], "verbose_name_plural": "plan categories"},
        ),
        migrations.AlterModelOptions(
            name="plan",
            options={"db_table": "plans_plan", "ordering": ["display_order", "monthly_price", "id"]},
        ),
    ]
