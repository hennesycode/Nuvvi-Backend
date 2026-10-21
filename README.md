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
| `MATIAS_API_PRODUCTION_BASE_URL` | `https://api.matias-api.com/api/ubl2.1` | MATIAS production API root (documented example); override only if MATIAS supplies a different root |

Copy `.env.example` to `.env` and customize.

MATIAS Sandbox uses the documented `https://sandbox-api.matias-api.com/api/ubl2.1` root; Production uses the documented `https://api.matias-api.com/api/ubl2.1` example. Production has a separate connection and PAT. Changing this environment variable does not overwrite a connection already stored in the database: update that connection in the MATIAS administration screen and validate it before registering production companies.

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

### Administración de planes

`GET /api/plans/?current=true` devuelve solo planes activos y publicados; el catálogo, sus contadores y los selectores de combos utilizan ese mismo criterio. `GET /api/plan-bundles/?current=true` filtra combos activos. Los registros anteriores y sus referencias se conservan.

La creación publica inmediatamente. La modalidad `quote_only` es independiente del tipo de servicio. Los límites `null` significan sin definir (según cotización en ofertas personalizadas); `0` conserva su significado numérico. Los combos admiten `features=null` para heredar los beneficios de sus componentes, o una lista explícita para personalizarlos.

Los precios de combos se calculan con `Decimal`, aplicando una sola vez el descuento a la suma del mismo período y redondeando a dos decimales con `ROUND_HALF_UP`. El frontend utiliza céntimos enteros con la misma política.

Antes de desplegar el frontend de administración, ejecutar `python manage.py migrate`: las migraciones `0008` y `0009` añaden la presentación del combo y corrigen los límites de marcador de la oferta empresarial sembrada anteriormente. No cambian precios ni descuentos ni eliminan referencias. Validación del módulo: `python manage.py test apps.plans`.

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
