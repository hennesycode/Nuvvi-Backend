#!/bin/sh
set -e

echo "==> Nuvvi Backend Entrypoint <=="

echo "==> Waiting for database..."
python scripts/wait_for_db.py

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Creating default superuser if needed..."
python scripts/create_default_superuser.py

echo "==> Starting application..."

if [ "$ENVIRONMENT" = "production" ]; then
    echo "==> Running Gunicorn (production)"
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
else
    echo "==> Running Django development server"
    exec python manage.py runserver 0.0.0.0:8000
fi
