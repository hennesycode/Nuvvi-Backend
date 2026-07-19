from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="status",
            field=models.CharField(choices=[("success", "Exitoso"), ("error", "Error"), ("warning", "Advertencia")], default="success", max_length=20),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="message",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="error_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="request_method",
            field=models.CharField(blank=True, max_length=12),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="request_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="auditlog",
            name="ip_address",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["-created_at"], name="audit_log_created_3e4fb8_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["status", "-created_at"], name="audit_log_status_07f9ad_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-created_at"], name="audit_log_action_41b63d_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["entity", "-created_at"], name="audit_log_entity_03b6d1_idx"),
        ),
    ]
