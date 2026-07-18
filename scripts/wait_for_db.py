#!/usr/bin/env python
import os
import sys
import time
from pathlib import Path

import django
from django.db import connections

MAX_RETRIES = 30
RETRY_DELAY = 2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

for attempt in range(1, MAX_RETRIES + 1):
    try:
        connections["default"].ensure_connection()
        print(f"Database is ready! (attempt {attempt})")
        break
    except Exception as e:
        print(f"Waiting for database... attempt {attempt}/{MAX_RETRIES}: {e}")
        if attempt == MAX_RETRIES:
            raise RuntimeError("Database not available after max retries")
        time.sleep(RETRY_DELAY)
