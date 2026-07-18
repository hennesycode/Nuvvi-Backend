#!/usr/bin/env python
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = os.environ.get("DEFAULT_SUPERUSER_EMAIL", "admin@nuvvi.local")
password = os.environ.get("DEFAULT_SUPERUSER_PASSWORD", "Admin12345*")
name = os.environ.get("DEFAULT_SUPERUSER_NAME", "Super Admin Nuvvi")

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password, full_name=name)
    print(f"Superuser created: {email}")
else:
    print(f"Superuser already exists: {email}")
