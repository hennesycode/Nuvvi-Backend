from django.db import migrations, models


def populate_usernames(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    used = set()
    for user in User.objects.order_by("id"):
        base = (user.email.split("@")[0] if user.email else f"usuario{user.id}").lower()
        base = "".join(char for char in base if char.isalnum() or char in "._-").strip("._-") or f"usuario{user.id}"
        username = base[:150]
        suffix = 1
        while username in used or User.objects.filter(username=username).exclude(pk=user.pk).exists():
            ending = f"-{suffix}"
            username = f"{base[:150 - len(ending)]}{ending}"
            suffix += 1
        user.username = username
        user.save(update_fields=["username"])
        used.add(username)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_admin_user_profile"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
        migrations.RunPython(populate_usernames, migrations.RunPython.noop),
    ]
