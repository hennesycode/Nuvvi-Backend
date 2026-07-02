# Nuvvi Backend

API backend for **Nuvvi by Hennesy** — SaaS de facturación electrónica, inventario y ventas.

Built with Django 5.x, Django REST Framework, PostgreSQL, Redis, and Celery.

---

## Tech Stack

- **Python 3.12+**
- **Django 5.x** with Django REST Framework
- **PostgreSQL 16** (primary database)
- **Redis 7** (cache / Celery broker)
- **JWT** authentication (simplejwt)
- **Docker** & Docker Compose

---

## Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or Docker)
- Redis 7+ (or Docker)

---

## Quick Start (Windows)

```powershell
cd "C:\Users\Usuario\Documents\Proyectos\Nuvvi\Nuvvi BACKEND"

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Quick Start with Docker

```bash
docker compose up --build
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | — | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DATABASE_URL` | `postgresql://...` | Database connection URL |
| `REDIS_URL` | `redis://...` | Redis connection URL |
| `CORS_ALLOWED_ORIGINS` | `localhost:5174` | Allowed CORS origins |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `60` | JWT access token lifetime |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `7` | JWT refresh token lifetime |
| `DEFAULT_SUPERUSER_*` | — | Auto-created superuser credentials |

Copy `.env.example` to `.env` and customize.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health/` | Health check |
| `GET` | `/api/schema/` | OpenAPI schema |
| `GET` | `/api/docs/` | Swagger UI |
| `POST` | `/api/auth/token/` | Obtain JWT token |
| `POST` | `/api/auth/token/refresh/` | Refresh JWT token |
| `GET` | `/api/auth/me/` | Current user info |
| `GET` | `/api/tenants/` | List tenants |
| `GET` | `/api/plans/` | List plans |
| `GET` | `/api/subscriptions/` | List subscriptions |

Full API docs at `/api/docs/` when running.

---

## Project Structure

```
Nuvvi BACKEND/
├── apps/
│   ├── accounts/       # Custom User model & auth
│   ├── tenants/        # Multi-tenant management
│   ├── plans/          # Subscription plans
│   ├── subscriptions/  # Tenant subscriptions
│   ├── api_keys/       # API key management
│   ├── dian/           # DIAN/MATIAS integration (placeholder)
│   ├── billing/        # Billing (placeholder)
│   ├── audit/          # Audit logs
│   └── core/           # Health check, permissions
├── config/
│   ├── settings/       # Settings per environment
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── scripts/            # Utility scripts
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

---

## Next Steps

1. Create real Celery tasks for async operations
2. Implement tenant isolation middleware
3. Add DIAN/MATIAS API integration
4. Build inventory, cash register, and sales modules
5. Add comprehensive test suite
