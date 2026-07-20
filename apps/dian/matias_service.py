import base64
import hashlib
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urljoin, urlparse

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log

from .models import MatiasCatalogSync, MatiasConnection


SANDBOX_URL = "https://sandbox-api.matias-api.com/api/ubl2.1"
PRODUCTION_URL = ""
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


def normalize_base_url(value):
    url = str(value or "").strip().rstrip("/")
    marker = "/api/ubl2.1"
    if marker in url:
        url = url[: url.find(marker) + len(marker)]
    return url


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


def get_connection(environment=None):
    environment = environment if environment in dict(MatiasConnection.ENVIRONMENT_CHOICES) else MatiasConnection.ENVIRONMENT_SANDBOX
    name = "MATIAS_PRODUCTION" if environment == MatiasConnection.ENVIRONMENT_PRODUCTION else "MATIAS_SANDBOX"
    connection, _ = MatiasConnection.objects.get_or_create(
        environment=environment,
        defaults={"name": name, "base_url": get_default_url(environment)},
    )
    if connection.name != name:
        connection.name = name
        connection.save(update_fields=["name"])
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
    except socket.timeout as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "status_code": 0, "headers": {}, "data": {}, "response_time_ms": elapsed, "error": str(exc), "error_type": "TIMEOUT", "endpoint": endpoint}
    except ssl.SSLError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "status_code": 0, "headers": {}, "data": {}, "response_time_ms": elapsed, "error": str(exc), "error_type": "SSL_ERROR", "endpoint": endpoint}
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {"ok": False, "status_code": 0, "headers": {}, "data": {}, "response_time_ms": elapsed, "error": str(exc), "error_type": "API_UNAVAILABLE", "endpoint": endpoint}


def get_records(data):
    if not isinstance(data, dict):
        return []
    records = data.get("dataRecords", {}).get("data")
    if isinstance(records, list):
        return records
    records = data.get("data")
    return records if isinstance(records, list) else []


def has_data_records(data):
    return isinstance(data, dict) and isinstance(data.get("dataRecords", {}).get("data"), list)


def response_success(data):
    return not isinstance(data, dict) or data.get("success", True) is True


def diagnostic(label, response, *, ok=None, detail=""):
    success = response["ok"] if ok is None else ok
    return {
        "label": label,
        "endpoint": response.get("endpoint", ""),
        "http_status": response.get("status_code") or None,
        "response_time_ms": response.get("response_time_ms"),
        "status": "success" if success else "error",
        "detail": detail or ("Correcto" if success else response.get("error") or "Error"),
    }


def extract_company(data):
    if isinstance(data, dict):
        company = data.get("data") if isinstance(data.get("data"), dict) else data.get("dataRecords", {}).get("data") if isinstance(data.get("dataRecords", {}).get("data"), dict) else data
        return {
            "uuid": company.get("uuid") or company.get("company_uuid") or company.get("parent_company_uuid") or "",
            "id": str(company.get("id") or company.get("external_id") or company.get("company_id") or ""),
            "name": company.get("name") or company.get("business_name") or company.get("legal_name") or "",
            "nit": str(company.get("nit") or company.get("identification_number") or ""),
            "email": company.get("email") or "",
            "status": str(company.get("status") or ""),
        }
    return {"uuid": "", "id": "", "name": "", "nit": "", "email": "", "status": ""}


def extract_user(data):
    if not isinstance(data, dict):
        return {"id": "", "email": ""}
    user = data.get("data") if isinstance(data.get("data"), dict) else data.get("user") if isinstance(data.get("user"), dict) else data
    return {"id": str(user.get("id") or user.get("uuid") or ""), "email": user.get("email") or ""}


def extract_membership(data):
    source = data.get("data") if isinstance(data, dict) and isinstance(data.get("data"), dict) else data if isinstance(data, dict) else {}
    return {
        "plan": source.get("plan") or source.get("plan_name") or source.get("name") or "",
        "status": source.get("status") or source.get("membership_status") or "",
        "expires_at": parse_matias_datetime(source.get("expires_at") or source.get("valid_until") or source.get("ends_at")),
        "documents_available": source.get("documents_available") or source.get("available_documents") or source.get("remaining_documents"),
        "documents_consumed": source.get("documents_consumed") or source.get("consumed_documents") or source.get("used_documents"),
        "company_limit": source.get("company_limit") or source.get("companies_limit") or source.get("customer_quota"),
        "raw": source,
    }


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
    status = MatiasConnection.STATUS_TESTING
    operational = MatiasConnection.OP_PAT_REQUIRED if not token else MatiasConnection.OP_PAT_VALID
    last_error = ""
    response_time = None
    server_ok = False
    pat_ok = False
    company_ok = False
    uuid_ok = False
    multicompany_ok = False
    membership_ok = False
    environment_ok = True

    if not connection.enabled:
        status = MatiasConnection.STATUS_DISABLED
        operational = MatiasConnection.OP_INACTIVE
        last_error = "La integración está desactivada."
        results.append({"label": "Integración activa", "status": "warning", "detail": last_error})
    if not connection.base_url.startswith("https://"):
        status = MatiasConnection.STATUS_CONFIGURATION_ERROR
        operational = MatiasConnection.OP_PAT_REQUIRED
        last_error = "La URL base debe usar HTTPS."
        results.append({"label": "URL disponible", "status": "error", "detail": last_error})
    elif not urlparse(connection.base_url).netloc:
        status = MatiasConnection.STATUS_CONFIGURATION_ERROR
        last_error = "La URL base no es válida."
        results.append({"label": "URL disponible", "status": "error", "detail": last_error})

    if connection.base_url.startswith("https://"):
        catalog = matias_request(connection, "/countries")
        records = get_records(catalog["data"])
        server_ok = catalog["ok"] and response_success(catalog["data"]) and has_data_records(catalog["data"])
        response_time = catalog["response_time_ms"]
        results.append(diagnostic("Servidor", catalog, ok=server_ok, detail="Catálogo público /countries disponible." if server_ok else "No se pudo acceder a los catálogos de MATIAS."))
        if not server_ok:
            error_type = catalog.get("error_type")
            status = MatiasConnection.STATUS_TIMEOUT if error_type == "TIMEOUT" else MatiasConnection.STATUS_CONFIGURATION_ERROR if error_type == "SSL_ERROR" else MatiasConnection.STATUS_API_UNAVAILABLE
            last_error = catalog["error"] or "No se pudo acceder a MATIAS."

    if not connection.enabled:
        pass
    elif not token:
        status = MatiasConnection.STATUS_NOT_CONFIGURED
        operational = MatiasConnection.OP_PAT_REQUIRED
        last_error = "No hay Personal Access Token configurado."
        results.append({"label": "Autenticación", "endpoint": "/auth/user", "http_status": None, "response_time_ms": None, "status": "error", "detail": last_error})
    elif is_token_expired(connection):
        status = MatiasConnection.STATUS_AUTHENTICATION_ERROR
        operational = MatiasConnection.OP_TOKEN_EXPIRED
        last_error = "El PAT guardado venció según la fecha devuelta por MATIAS."
        results.append({"label": "Autenticación", "endpoint": "/auth/user", "http_status": None, "response_time_ms": None, "status": "error", "detail": last_error})
    else:
        auth = matias_request(connection, "/auth/user", token=token)
        pat_ok = auth["ok"] and response_success(auth["data"])
        if pat_ok:
            user = extract_user(auth["data"])
            connection.authenticated_user_id = user["id"]
            connection.authenticated_user_email = user["email"]
            connection.account_email = user["email"] or connection.account_email
            results.append(diagnostic("Autenticación", auth, detail=f"Usuario autenticado{': ' + user['email'] if user['email'] else '.'}"))
        else:
            status = MatiasConnection.STATUS_AUTHENTICATION_ERROR if auth["status_code"] in (401, 403) else MatiasConnection.STATUS_API_UNAVAILABLE
            last_error = auth["error"] or f"HTTP {auth['status_code']}"
            operational = MatiasConnection.OP_TOKEN_EXPIRED if "expired" in last_error.lower() or "venc" in last_error.lower() else MatiasConnection.OP_PAT_REQUIRED
            results.append(diagnostic("Autenticación", auth, ok=False, detail=last_error))

        company_response = matias_request(connection, "/company", token=token)
        if pat_ok and company_response["ok"]:
            company = extract_company(company_response["data"])
            connection.external_company_id = company["id"]
            connection.external_company_name = company["name"]
            connection.external_company_nit = company["nit"]
            connection.external_company_status = company["status"]
            connection.account_main_email = company["email"] or connection.account_email
            company_ok = bool(company["id"] or company["name"] or company["nit"] or company["uuid"])
            if company["uuid"]:
                connection.parent_company_uuid = company["uuid"]
            uuid_ok = bool(connection.parent_company_uuid)
            operational = MatiasConnection.OP_PARENT_UUID_REQUIRED if not uuid_ok else operational
            results.append(diagnostic("Empresa", company_response, ok=company_ok, detail=company["name"] or "Empresa detectada." if company_ok else "No fue posible detectar la empresa principal."))
        else:
            if pat_ok:
                operational = MatiasConnection.OP_ACCOUNT_NOT_DETECTED
                last_error = company_response["error"] or f"HTTP {company_response['status_code']}"
            results.append(diagnostic("Empresa", company_response, ok=False, detail=last_error or "Pendiente de PAT válido."))

        customers = matias_request(connection, "/company/customers", token=token)
        if pat_ok and customers["ok"]:
            data = get_records(customers["data"])
            connection.linked_companies_count = len(data) if isinstance(data, list) else connection.linked_companies_count
            connection.multicompany_verified = True
            multicompany_ok = True
            operational = MatiasConnection.OP_MULTICOMPANY_VERIFIED
            results.append(diagnostic("Multiempresa", customers, detail="Puede consultar empresas vinculadas."))
        else:
            connection.multicompany_verified = False
            if pat_ok:
                operational = MatiasConnection.OP_MULTICOMPANY_PENDING
                last_error = customers["error"] or f"HTTP {customers['status_code']}"
            results.append(diagnostic("Multiempresa", customers, ok=False, detail=last_error or "Pendiente de PAT válido."))

        membership = matias_request(connection, "/memberships/summary", token=token)
        if pat_ok and membership["ok"]:
            summary = extract_membership(membership["data"])
            connection.membership_plan = summary["plan"]
            connection.membership_status = summary["status"]
            connection.membership_expires_at = summary["expires_at"]
            connection.membership_documents_available = summary["documents_available"]
            connection.membership_documents_consumed = summary["documents_consumed"]
            connection.membership_company_limit = summary["company_limit"]
            connection.membership_summary = summary["raw"]
            membership_ok = not summary["status"] or str(summary["status"]).lower() in ("active", "activo", "valid", "vigente")
            if not membership_ok:
                operational = MatiasConnection.OP_MEMBERSHIP_INACTIVE
            results.append(diagnostic("Membresía", membership, ok=membership_ok, detail=summary["plan"] or "Resumen de membresía consultado."))
        else:
            if pat_ok:
                operational = MatiasConnection.OP_MEMBERSHIP_INACTIVE
                last_error = membership["error"] or f"HTTP {membership['status_code']}"
            results.append(diagnostic("Membresía", membership, ok=False, detail=last_error or "Pendiente de PAT válido."))

        detected = (auth.get("headers", {}).get("X-MATIAS-Environment") or "").lower()
        connection.environment_detected = detected
        if connection.environment == MatiasConnection.ENVIRONMENT_SANDBOX and detected and detected != connection.environment:
            status = MatiasConnection.STATUS_ENVIRONMENT_MISMATCH
            environment_ok = False
            last_error = f"Ambiente detectado {detected}, configurado {connection.environment}."
            results.append({"label": "Ambiente", "endpoint": "/auth/user", "http_status": auth.get("status_code"), "response_time_ms": auth.get("response_time_ms"), "status": "error", "detail": last_error})
        else:
            results.append({"label": "Ambiente", "endpoint": "/auth/user", "http_status": auth.get("status_code"), "response_time_ms": auth.get("response_time_ms"), "status": "success", "detail": detected or connection.environment})

    if not connection.enabled:
        status = MatiasConnection.STATUS_DISABLED
        operational = MatiasConnection.OP_INACTIVE
    elif status not in (MatiasConnection.STATUS_DISABLED, MatiasConnection.STATUS_NOT_CONFIGURED, MatiasConnection.STATUS_AUTHENTICATION_ERROR, MatiasConnection.STATUS_API_UNAVAILABLE, MatiasConnection.STATUS_TIMEOUT, MatiasConnection.STATUS_CONFIGURATION_ERROR, MatiasConnection.STATUS_ENVIRONMENT_MISMATCH):
        status = MatiasConnection.STATUS_CONNECTED if server_ok and pat_ok else MatiasConnection.STATUS_AUTHENTICATION_ERROR
    if server_ok and environment_ok and pat_ok and company_ok and uuid_ok and multicompany_ok and membership_ok and connection.catalogs_status == MatiasConnection.CATALOGS_SYNCED:
        operational = MatiasConnection.OP_READY
    elif connection.catalogs_status == MatiasConnection.CATALOGS_PARTIAL:
        operational = MatiasConnection.OP_CATALOGS_PARTIAL
    elif connection.catalogs_status != MatiasConnection.CATALOGS_SYNCED and operational in (MatiasConnection.OP_MULTICOMPANY_VERIFIED, MatiasConnection.OP_PAT_VALID):
        operational = MatiasConnection.OP_CATALOGS_PENDING

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
    attempted_at = timezone.now()
    if not connection.base_url.startswith("https://"):
        connection.catalogs_status = MatiasConnection.CATALOGS_ERROR
        connection.catalogs_last_attempt_at = attempted_at
        connection.last_error_at = attempted_at
        connection.last_error_code = "CATALOGS_UNAVAILABLE"
        connection.last_error_message = "No se pudo acceder a los catálogos de MATIAS."
        connection.save()
        write_audit_log(request=request, action="matias_catalogos_error", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_ERROR, message="Sincronización de catálogos fallida.", error_message=connection.last_error_message)
        return connection

    for endpoint, label in CATALOG_ENDPOINTS:
        response = matias_request(connection, f"/{endpoint}")
        data = get_records(response["data"])
        valid = response["ok"] and response_success(response["data"]) and has_data_records(response["data"])
        count = len(data) if isinstance(data, list) else None
        item_status = "Sincronizado" if valid else "Error"
        if valid:
            synced += 1
        sync, _ = MatiasCatalogSync.objects.get_or_create(connection=connection, endpoint=f"/{endpoint}", defaults={"catalog_name": label})
        sync.catalog_name = label
        sync.status = MatiasConnection.CATALOGS_SYNCED if valid else MatiasConnection.CATALOGS_ERROR
        sync.records_count = count
        sync.last_attempt_at = attempted_at
        if valid:
            sync.last_success_at = attempted_at
            sync.error_message = ""
        else:
            sync.error_message = response["error"] or "Respuesta de catálogo inválida."
        sync.http_status = response["status_code"] or None
        sync.response_time_ms = response["response_time_ms"]
        sync.save()
        details.append({"endpoint": f"/{endpoint}", "name": label, "records": count, "status": item_status, "last_attempt_at": attempted_at.isoformat(), "last_synced_at": sync.last_success_at.isoformat() if sync.last_success_at else "", "http_status": sync.http_status, "response_time_ms": sync.response_time_ms, "error": "" if valid else sync.error_message})

    connection.catalogs_total_count = len(CATALOG_ENDPOINTS)
    connection.catalogs_synced_count = synced
    connection.catalogs_status = MatiasConnection.CATALOGS_SYNCED if synced == len(CATALOG_ENDPOINTS) else MatiasConnection.CATALOGS_PARTIAL if synced else MatiasConnection.CATALOGS_ERROR
    connection.catalogs_last_attempt_at = attempted_at
    if connection.catalogs_status == MatiasConnection.CATALOGS_SYNCED:
        connection.catalogs_last_synced_at = attempted_at
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


def store_validated_pat(connection, pat, *, token_name="", token_external_id="", token_expires_at=None, token_created_at=None, account_email="", request=None):
    auth = matias_request(connection, "/auth/user", token=pat)
    if not auth["ok"] or not response_success(auth["data"]):
        write_audit_log(request=request, action="matias_pat_validacion_fallida", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_ERROR, message="PAT de MATIAS rechazado; se conservó el token anterior.", error_message=auth["error"] or f"HTTP {auth['status_code']}")
        raise ValueError("MATIAS rechazó el PAT. Se conservó el token anterior.")
    user = extract_user(auth["data"])
    connection.encrypted_access_token = encrypt_secret(pat)
    connection.token_name = token_name or connection.token_name
    connection.token_external_id = token_external_id or connection.token_external_id
    connection.token_expires_at = token_expires_at
    connection.token_created_at = token_created_at or timezone.now()
    connection.authenticated_user_id = user["id"]
    connection.authenticated_user_email = user["email"]
    connection.account_email = user["email"] or account_email or connection.account_email
    connection.connection_status = MatiasConnection.STATUS_CONNECTED
    connection.operational_status = MatiasConnection.OP_PAT_VALID
    connection.last_error_code = ""
    connection.last_error_message = ""
    connection.save()
    return connection


def generate_pat(connection, *, email, password, token_name, description, expires_in_days, request=None):
    access_token = None
    try:
        login = matias_request(connection, "/auth/login", method="POST", payload={"email": email, "password": password, "remember_me": 0})
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

        connection = store_validated_pat(
            connection,
            pat,
            token_name=token_name,
            token_external_id=str(data.get("id") or data.get("token_id") or ""),
            token_expires_at=parse_matias_datetime(data.get("expires_at") or data.get("expiresAt") or data.get("expiration_date") or data.get("valid_until")),
            token_created_at=parse_matias_datetime(data.get("created_at") or data.get("createdAt")) or timezone.now(),
            account_email=email,
            request=request,
        )
        write_audit_log(request=request, action="matias_pat_generado", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_SUCCESS, message="PAT de MATIAS generado, validado y guardado cifrado.", metadata={"email": email, "token_name": token_name, "environment": connection.environment})
        return connection
    finally:
        if access_token:
            matias_request(connection, "/auth/logout", token=access_token)
        password = None
        access_token = None


def revoke_current_pat(connection, request=None):
    token = decrypt_secret(connection.encrypted_access_token)
    if not token or not connection.token_external_id:
        raise ValueError("No hay PAT con ID externo para revocar.")
    response = matias_request(connection, f"/tokens/{connection.token_external_id}", method="DELETE", token=token)
    if not response["ok"]:
        write_audit_log(request=request, action="matias_pat_revocacion_error", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_ERROR, message="No se pudo revocar el PAT actual.", error_message=response["error"] or f"HTTP {response['status_code']}")
        raise ValueError("No se pudo revocar el PAT actual en MATIAS.")
    connection.encrypted_access_token = ""
    connection.token_external_id = ""
    connection.token_expires_at = None
    connection.token_created_at = None
    connection.connection_status = MatiasConnection.STATUS_NOT_CONFIGURED
    connection.operational_status = MatiasConnection.OP_PAT_REQUIRED
    connection.save()
    write_audit_log(request=request, action="matias_pat_revocado", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_SUCCESS, message="PAT actual revocado en MATIAS.", metadata={"environment": connection.environment})
    return connection
