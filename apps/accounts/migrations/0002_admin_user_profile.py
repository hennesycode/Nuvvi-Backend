from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="first_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="last_name",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="admin_role",
            field=models.CharField(blank=True, choices=[("superadmin", "Superadministrador"), ("finance", "Finanzas y cartera"), ("support", "Soporte")], max_length=30),
        ),
        migrations.AddField(
            model_name="user",
            name="identification_type",
            field=models.CharField(blank=True, choices=[("cc", "Cédula de ciudadanía"), ("ce", "Cédula de extranjería"), ("nit", "NIT"), ("passport", "Pasaporte")], max_length=20),
        ),
        migrations.AddField(
            model_name="user",
            name="identification_number",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="user",
            name="country",
            field=models.CharField(default="Colombia", max_length=80),
        ),
        migrations.AddField(
            model_name="user",
            name="department",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="city",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="address",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_country_code",
            field=models.CharField(default="+57", max_length=8),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_number",
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name="user",
            name="password_setup_token_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="user",
            name="password_setup_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="password_setup_used_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="invitation_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
