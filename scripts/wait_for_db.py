#!/usr/bin/env python
import time
import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://nuvvi:nuvvi_password@db:5432/nuvvi_db")

MAX_RETRIES = 30
RETRY_DELAY = 2

for attempt in range(1, MAX_RETRIES + 1):
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=5)
        conn.close()
        print(f"Database is ready! (attempt {attempt})")
        break
    except Exception as e:
        print(f"Waiting for database... attempt {attempt}/{MAX_RETRIES}: {e}")
        if attempt == MAX_RETRIES:
            raise RuntimeError("Database not available after max retries")
        time.sleep(RETRY_DELAY)
