Write-Host "====================================="  -ForegroundColor Green
Write-Host "  Nuvvi Backend — Development Start"  -ForegroundColor Green
Write-Host "====================================="  -ForegroundColor Green

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
. .venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "Running migrations..." -ForegroundColor Yellow
python manage.py migrate

if ($env:CREATE_DEFAULT_SUPERUSER -eq "true") {
    Write-Host "Creating default superuser..." -ForegroundColor Yellow
    python scripts/create_default_superuser.py
} else {
    Write-Host "Skipping default superuser creation" -ForegroundColor Yellow
}

Write-Host "Starting development server..." -ForegroundColor Green
python manage.py runserver 0.0.0.0:8000
