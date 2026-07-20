import base64
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urljoin

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log

from .models import MatiasConnection


SANDBOX_URL = "https://sandbox-api.matias-api.com/api/ubl2.1"
PRODUCTION_URL = "https://api-v2.matias-api.com/api/ubl2.1"
CATALOG_ENDPOINTS = [
    ("destination-environment", "Ambientes destino"),
    ("document-type", "Tipos de documento"),
    ("payment-methods", "Métodos de pago"),
    ("payment-means", "Medios de pago"),
    ("identity-documents", "Tipos de identificación"),
    ("fiscal-regime", "Régimen fiscal"),
    ("accounting-regime", "Régimen contable"),
    ("delivery-conditions", "Condiciones de entrega"),
    ("correction-notes", "Notas de corrección"),
    ("discount-codes", "Códigos de descuento"),
    ("operation-type", "Tipos de operación"),
    ("taxes", "Impuestos"),
    ("quantity-units", "Unidades de medida"),
    ("reference-price", "Precios de referencia"),
    ("cities", "Ciudades"),
    ("departments", "Departamentos"),
    ("countries", "Países"),
    ("currencies", "Monedas"),
]


def get_default_url(environment):
    return PRODUCTION_URL if environment == MatiasConnection.ENVIRONMENT_PRODUCTION else SANDBOX_URL


def get_cipher():
    raw_key = getattr(settings, "MATIAS_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value):
    if not value:
        return ""
    return get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value):
    if not value:
        return ""
    return get_cipher().decrypt(value.encode("utf-8")).decode("utf-8")


def mask_token(token):
    if not token:
        return "Sin configurar"
    if len(token) <= 12:
        return f"{token[:3]}••••{token[-3:]}"
    return f"{token[:8]}••••••••{token[-4:]}"


def get_connection():
    connection, _ = MatiasConnection.objects.get_or_create(
        name="MATIAS API",
        defaults={"base_url": SANDBOX_URL, "environment": MatiasConnection.ENVIRONMENT_SANDBOX},
    )
    return connection


def matias_request(connection, endpoint, *, method="GET", token=None, payload=None, timeout=None):
    base_url = connection.base_url.rstrip("/") + "/"
    url = urljoin(base_url, endpoint.lstrip("/"))
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout or connection.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            elapsed = int((time.perf_counter() - started) * 1000)
            return {
                "ok": 200 <= response.status < 300,
                "status_code": response.status,
                "headers": dict(response.headers.items()),
                "data": json.loads(raw) if raw else {},
                "response_time_ms": elapsed,
                "error": "",
                "endpoint": endpoint,
            }
    except urllib.error.HTTPError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        raw = exc.read().decode("utf-8", errors="ignore")
        return {"ok": False, "status_code": exc.code, "headers": dict(exc.headers.items()), "data": {}, "response_time_ms": elapsed, "error": raw or str(exc), "endpoint": endpoint}
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "status_code": 0, "headers": {}, "data": {}, "response_time_ms": elapsed, "error": str(exc), "endpoint": endpoint}


def extract_company(data):
    if isinstance(data, dict):
        company = data.get("data") if isinstance(data.get("data"), dict) else data
        return {
            "uuid": company.get("uuid") or company.get("id") or company.get("company_uuid") or "",
            "id": str(company.get("id") or company.get("external_id") or ""),
            "name": company.get("name") or company.get("business_name") or company.get("legal_name") or "",
            "nit": str(company.get("nit") or company.get("identification_number") or ""),
            "email": company.get("email") or "",
        }
    return {"uuid": "", "id": "", "name": "", "nit": "", "email": ""}


def parse_matias_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if timezone.is_aware(value) else timezone.make_aware(value)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)
        except ValueError:
            return None
    return None


def is_token_expired(connection):
    return bool(connection.encrypted_access_token and connection.token_expires_at and connection.token_expires_at <= timezone.now())


def run_connection_test(connection, request=None):
    token = decrypt_secret(connection.encrypted_access_token)
    now = timezone.now()
    results = []
    status = MatiasConnection.STATUS_CONNECTED
    operational = MatiasConnection.OP_READY
    last_error = ""
    response_time = None

    if not connection.enabled:
        status = MatiasConnection.STATUS_DISABLED
        operational = MatiasConnection.OP_INACTIVE
        last_error = "La integración está desactivada."
        results.append({"label": "Integración activa", "status": "warning", "detail": last_error})
    elif not connection.base_url.startswith("https://"):
        status = MatiasConnection.STATUS_CONFIGURATION_ERROR
        operational = MatiasConnection.OP_PARENT_NOT_FOUND
        last_error = "La URL base debe usar HTTPS."
        results.append({"label": "URL disponible", "status": "error", "detail": last_error})
    else:
        results.append({"label": "URL válida HTTPS", "status": "success", "detail": "Configuración básica correcta."})

    if status in (MatiasConnection.STATUS_DISABLED, MatiasConnection.STATUS_CONFIGURATION_ERROR):
        pass
    elif not token:
        status = MatiasConnection.STATUS_NOT_CONFIGURED
        operational = MatiasConnection.OP_PAT_REQUIRED
        last_error = "No hay Personal Access Token configurado."
        results.append({"label": "Token válido", "status": "error", "detail": last_error})
    elif is_token_expired(connection):
        status = MatiasConnection.STATUS_AUTHENTICATION_ERROR
        operational = MatiasConnection.OP_TOKEN_EXPIRED
        last_error = "El PAT guardado venció según la fecha devuelta por MATIAS."
        results.append({"label": "Token válido", "status": "error", "detail": last_error})
    else:
        auth = matias_request(connection, "/auth/user", token=token)
        response_time = auth["response_time_ms"]
        if auth["ok"]:
            results.append({"label": "Token válido", "status": "success", "detail": "Usuario autenticado."})
        else:
            status = MatiasConnection.STATUS_AUTHENTICATION_ERROR if auth["status_code"] in (401, 403) else MatiasConnection.STATUS_API_UNAVAILABLE
            last_error = auth["error"] or f"HTTP {auth['status_code']}"
            operational = MatiasConnection.OP_TOKEN_EXPIRED if "expired" in last_error.lower() or "venc" in last_error.lower() else MatiasConnection.OP_PAT_REQUIRED
            results.append({"label": "Token válido", "status": "error", "detail": last_error})

        company_response = matias_request(connection, "/company", token=token)
        if company_response["ok"]:
            company = extract_company(company_response["data"])
            connection.external_company_id = company["id"]
            connection.external_company_name = company["name"]
            connection.external_company_nit = company["nit"]
            connection.account_main_email = company["email"] or connection.account_email
            if company["uuid"] and not connection.parent_company_uuid:
                connection.parent_company_uuid = company["uuid"]
            results.append({"label": "Empresa principal encontrada", "status": "success", "detail": company["name"] or "Empresa detectada."})
        else:
            status = MatiasConnection.STATUS_CONFIGURATION_ERROR
            operational = MatiasConnection.OP_PARENT_NOT_FOUND
            last_error = company_response["error"] or f"HTTP {company_response['status_code']}"
            results.append({"label": "Empresa principal encontrada", "status": "error", "detail": last_error})

        customers = matias_request(connection, "/company/customers", token=token)
        if customers["ok"]:
            data = customers["data"].get("data", customers["data"])
            connection.linked_companies_count = len(data) if isinstance(data, list) else connection.linked_companies_count
            connection.multicompany_verified = True
            results.append({"label": "Permiso multiempresa", "status": "success", "detail": "Puede consultar empresas vinculadas."})
        else:
            connection.multicompany_verified = False
            operational = MatiasConnection.OP_MULTICOMPANY_DENIED
            last_error = customers["error"] or f"HTTP {customers['status_code']}"
            results.append({"label": "Permiso multiempresa", "status": "error", "detail": last_error})

        detected = (auth.get("headers", {}).get("X-MATIAS-Environment") or "").lower()
        connection.environment_detected = detected
        if detected and detected != connection.environment:
            status = MatiasConnection.STATUS_CONFIGURATION_ERROR
            last_error = f"Ambiente detectado {detected}, configurado {connection.environment}."
            results.append({"label": "Ambiente confirmado", "status": "error", "detail": last_error})
        else:
            results.append({"label": "Ambiente confirmado", "status": "success", "detail": detected or connection.environment})

        catalog = matias_request(connection, "/countries")
        if catalog["ok"]:
            results.append({"label": "Catálogos disponibles", "status": "success", "detail": "Endpoint /countries disponible."})
        else:
            operational = MatiasConnection.OP_CATALOGS_NOT_SYNCED
            results.append({"label": "Catálogos disponibles", "status": "warning", "detail": catalog["error"] or f"HTTP {catalog['status_code']}"})

    if connection.catalogs_status != MatiasConnection.CATALOGS_SYNCED and operational == MatiasConnection.OP_READY:
        operational = MatiasConnection.OP_CATALOGS_NOT_SYNCED

    connection.connection_status = status
    connection.operational_status = operational
    connection.last_test_at = now
    connection.last_response_time_ms = response_time
    connection.last_test_results = results
    if status == MatiasConnection.STATUS_CONNECTED and operational == MatiasConnection.OP_READY:
        connection.last_success_at = now
        connection.last_error_code = ""
        connection.last_error_message = ""
    elif last_error:
        connection.last_error_at = now
        connection.last_error_code = status
        connection.last_error_message = last_error
    connection.save()

    write_audit_log(
        request=request,
        action="matias_conexion_probada",
        entity="MatiasConnection",
        entity_id=connection.id,
        status=AuditLog.STATUS_SUCCESS if status == MatiasConnection.STATUS_CONNECTED else AuditLog.STATUS_ERROR,
        message="Prueba de conexión MATIAS ejecutada.",
        error_message=connection.last_error_message,
        metadata={"connection_status": status, "operational_status": operational, "environment": connection.environment},
    )
    return connection


def sync_catalogs(connection, request=None):
    details = []
    synced = 0
    if not connection.base_url.startswith("https://"):
        connection.catalogs_status = MatiasConnection.CATALOGS_ERROR
        connection.last_error_at = timezone.now()
        connection.last_error_code = "CATALOGS_UNAVAILABLE"
        connection.last_error_message = "No se pudo acceder a los catálogos de MATIAS."
        connection.save()
        write_audit_log(request=request, action="matias_catalogos_error", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_ERROR, message="Sincronización de catálogos fallida.", error_message=connection.last_error_message)
        return connection

    for endpoint, label in CATALOG_ENDPOINTS:
        response = matias_request(connection, f"/{endpoint}")
        data = response["data"].get("data", response["data"])
        count = len(data) if isinstance(data, list) else None
        item_status = "Sincronizado" if response["ok"] else "Error"
        if response["ok"]:
            synced += 1
        details.append({"endpoint": endpoint, "name": label, "records": count, "status": item_status, "last_synced_at": timezone.localtime().strftime("%d/%m/%Y %I:%M:%S %p"), "error": "" if response["ok"] else response["error"]})

    connection.catalogs_total_count = len(CATALOG_ENDPOINTS)
    connection.catalogs_synced_count = synced
    connection.catalogs_status = MatiasConnection.CATALOGS_SYNCED if synced == len(CATALOG_ENDPOINTS) else MatiasConnection.CATALOGS_ERROR
    connection.catalogs_last_synced_at = timezone.now()
    connection.catalogs_detail = details
    if connection.catalogs_status == MatiasConnection.CATALOGS_ERROR:
        connection.last_error_at = timezone.now()
        connection.last_error_code = "CATALOGS_UNAVAILABLE"
        connection.last_error_message = "No se pudo acceder a los catálogos de MATIAS."
    if connection.catalogs_status == MatiasConnection.CATALOGS_SYNCED and connection.connection_status == MatiasConnection.STATUS_CONNECTED and connection.multicompany_verified:
        connection.operational_status = MatiasConnection.OP_READY
    connection.save()
    write_audit_log(request=request, action="matias_catalogos_sincronizados", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_SUCCESS if connection.catalogs_status == MatiasConnection.CATALOGS_SYNCED else AuditLog.STATUS_WARNING, message=f"Catálogos sincronizados: {synced}/{len(CATALOG_ENDPOINTS)}.", metadata={"synced": synced, "total": len(CATALOG_ENDPOINTS)})
    return connection


def generate_pat(connection, *, email, password, token_name, description, expires_in_days, request=None):
    login = matias_request(connection, "/auth/login", method="POST", payload={"email": email, "password": password, "remember_me": False})
    if not login["ok"]:
        write_audit_log(request=request, action="matias_pat_login_fallido", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_ERROR, message="No se pudo iniciar sesión en MATIAS para generar PAT.", error_message=login["error"] or f"HTTP {login['status_code']}", metadata={"email": email})
        raise ValueError("No se pudo iniciar sesión en MATIAS para generar el PAT.")

    access_token = login["data"].get("access_token") or login["data"].get("token")
    if not access_token:
        raise ValueError("MATIAS no retornó access_token temporal.")

    endpoint = connection.token_generation_endpoint or "/tokens"
    token_response = matias_request(connection, endpoint, method="POST", token=access_token, payload={"name": token_name, "description": description, "expires_in_days": expires_in_days})
    if endpoint == "/tokens" and token_response["status_code"] == 404:
        token_response = matias_request(connection, "/auth/token", method="POST", token=access_token, payload={"name": token_name, "description": description, "expires_in_days": expires_in_days})
    if not token_response["ok"]:
        write_audit_log(request=request, action="matias_pat_generacion_fallida", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_ERROR, message="No se pudo generar el PAT de MATIAS.", error_message=token_response["error"] or f"HTTP {token_response['status_code']}")
        raise ValueError("No se pudo generar el PAT de MATIAS.")

    data = token_response["data"].get("data", token_response["data"])
    pat = data.get("plain_text_token") or data.get("access_token") or data.get("token")
    if not pat:
        raise ValueError("MATIAS no retornó el PAT generado.")

    connection.encrypted_access_token = encrypt_secret(pat)
    connection.token_name = token_name
    connection.token_external_id = str(data.get("id") or data.get("token_id") or "")
    connection.account_email = email
    connection.token_expires_at = parse_matias_datetime(data.get("expires_at") or data.get("expiresAt") or data.get("expiration_date") or data.get("valid_until"))
    if connection.enabled:
        connection.connection_status = MatiasConnection.STATUS_DISCONNECTED
        connection.operational_status = MatiasConnection.OP_CATALOGS_NOT_SYNCED
    connection.save()
    write_audit_log(request=request, action="matias_pat_generado", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_SUCCESS, message="PAT de MATIAS generado y guardado cifrado.", metadata={"email": email, "token_name": token_name})
    return connection
