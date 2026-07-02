#!/bin/sh
set -e

echo "====================================="
echo "  Nuvvi Backend — Development Start"
echo "====================================="

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

echo "Activating virtual environment..."
. .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Creating default superuser..."
python scripts/create_default_superuser.py

echo "Starting development server..."
python manage.py runserver 0.0.0.0:8000
