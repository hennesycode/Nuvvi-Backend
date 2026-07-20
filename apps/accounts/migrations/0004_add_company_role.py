from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_username"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="admin_role",
            field=models.CharField(blank=True, choices=[("superadmin", "Superadministrador"), ("finance", "Finanzas y cartera"), ("support", "Soporte"), ("company", "Empresa")], max_length=30),
        ),
    ]
