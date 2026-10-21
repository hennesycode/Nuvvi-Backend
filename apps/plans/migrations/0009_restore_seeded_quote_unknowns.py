from django.db import migrations


def restore_unknown_limits(apps, schema_editor):
    # 0007 wrote placeholder zeros into this specific personalized offer.
    # Do not reinterpret zeros in other offers, or overwrite configured values.
    Plan = apps.get_model("plans", "Plan")
    plans = Plan.objects.using(schema_editor.connection.alias).filter(
        code="nuvvi-empresarial", quote_only=True, plan_type="enterprise",
        short_description="Solución empresarial con alcance personalizado.",
    )
    fields = ("annual_document_quota", "max_documents_per_month", "max_users", "accountant_users", "max_employees", "max_branches")
    for plan in plans:
        changed = []
        for field in fields:
            if getattr(plan, field) == 0:
                setattr(plan, field, None)
                changed.append(field)
        if changed:
            plan.save(using=schema_editor.connection.alias, update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("plans", "0008_bundle_presentation")]
    operations = [migrations.RunPython(restore_unknown_limits, migrations.RunPython.noop)]
