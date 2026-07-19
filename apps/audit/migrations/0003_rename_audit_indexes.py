from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0002_auditlog_details"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="auditlog",
            new_name="audit_log_created_e49a79_idx",
            old_name="audit_log_created_3e4fb8_idx",
        ),
        migrations.RenameIndex(
            model_name="auditlog",
            new_name="audit_log_status_e28992_idx",
            old_name="audit_log_status_07f9ad_idx",
        ),
        migrations.RenameIndex(
            model_name="auditlog",
            new_name="audit_log_action_7c9e02_idx",
            old_name="audit_log_action_41b63d_idx",
        ),
        migrations.RenameIndex(
            model_name="auditlog",
            new_name="audit_log_entity_3eaefc_idx",
            old_name="audit_log_entity_03b6d1_idx",
        ),
    ]
