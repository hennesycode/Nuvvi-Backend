import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0004_plan_catalog_lifecycle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plan",
            name="monthly_price",
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=12, null=True),
        ),
        migrations.AlterField(
            model_name="plan",
            name="yearly_price",
            field=models.DecimalField(blank=True, decimal_places=2, default=None, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="plan",
            name="parent_plan",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="versions", to="plans.plan"),
        ),
        migrations.AddField(
            model_name="plan",
            name="version_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddConstraint(
            model_name="plan",
            constraint=models.UniqueConstraint(condition=Q(parent_plan__isnull=False), fields=("parent_plan", "version_number"), name="plans_unique_child_version"),
        ),
    ]
