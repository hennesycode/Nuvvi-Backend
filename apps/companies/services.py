import time

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log
from apps.dian.matias_service import decrypt_secret, get_connection, get_records, matias_request, sanitized_payload
from apps.dian.models import MatiasConnection

from .models import Company, CompanyProviderLink, CompanySyncAttempt


class CompanyValidationError(ValueError):
    pass


def normalize_nit(value):
    return "".join(ch for ch in str(value or "").strip().upper() if ch.isalnum())


def normalize_email(value):
    return str(value or "").strip().lower()


def remote_records(data):
    records = get_records(data)
    if records:
        return records
    if isinstance(data, dict) and isinstance(data.get("customers"), list):
        return data["customers"]
    return []


def extract_remote_company(raw):
    if not isinstance(raw, dict):
        return {"id": "", "client_uuid": "", "name": "", "nit": "", "email": "", "enabled": False, "status": "", "subscription": {}, "raw": {}}
    data = raw.get("data") if isinstance(raw.get("data"), dict) else raw.get("company") if isinstance(raw.get("company"), dict) else raw
    enabled = data.get("enabled")
    if enabled is None:
        enabled = data.get("active")
    return {
        "id": str(data.get("id") or data.get("company_id") or data.get("matias_company_id") or data.get("external_id") or ""),
        "client_uuid": str(data.get("client_uuid") or data.get("uuid") or data.get("company_uuid") or data.get("customer_uuid") or ""),
        "name": data.get("company_name") or data.get("name") or data.get("business_name") or data.get("legal_name") or "",
        "nit": normalize_nit(data.get("dni") or data.get("nit") or data.get("identification_number") or ""),
        "email": normalize_email(data.get("email") or ""),
        "enabled": enabled in (True, 1, "1", "true", "TRUE", "active", "ACTIVE"),
        "status": str(data.get("status") or data.get("state") or ""),
        "subscription": data.get("subscription") if isinstance(data.get("subscription"), dict) else {},
        "raw": sanitized_payload(data),
    }


class MatiasCompanyClient:
    def __init__(self, connection=None):
        self.connection = connection or get_connection()
        self.token = decrypt_secret(self.connection.encrypted_access_token)

    def _request(self, endpoint, *, method="GET", payload=None):
        return matias_request(self.connection, endpoint, method=method, token=self.token, payload=payload)

    def list_companies(self):
        return self._request("/company/customers")

    def create_company(self, *, parent_uuid, payload):
        return self._request(f"/company/{parent_uuid}/customer", method="POST", payload=payload)

    def get_company(self, *, client_uuid):
        return self._request(f"/company?client_uuid={client_uuid}")

    def update_company(self, *, company_id, client_uuid, payload):
        return self._request(f"/company/{company_id}?client_uuid={client_uuid}", method="PUT", payload=payload)

    def disable_company(self, *, company_id):
        return self._request(f"/company/customer/{company_id}", method="DELETE")

    def enable_company(self, *, company_id):
        return self._request(f"/company/customer/{company_id}/enable", method="POST")

    def get_company_stats(self, *, client_uuid):
        return self._request(f"/company/customers/{client_uuid}/stats")

    def get_settings(self, *, client_uuid):
        return self._request(f"/company/settings?client_uuid={client_uuid}")

    def update_setting(self, *, client_uuid, key, value):
        return self._request(f"/company/settings?client_uuid={client_uuid}", method="PUT", payload={"setting_key": key, "setting_value": value})


class CompanyApplicationService:
    def __init__(self, *, user=None, request=None, environment=None):
        self.user = user
        self.request = request
        self.connection = get_connection(environment)
        self.client = MatiasCompanyClient(self.connection)

    def ensure_ready(self):
        if not self.connection.enabled:
            raise CompanyValidationError("La conexión MATIAS está desactivada.")
        if self.connection.operational_status != MatiasConnection.OP_READY:
            raise CompanyValidationError("La conexión MATIAS debe estar en READY_TO_REGISTER_COMPANIES.")
        if not self.connection.parent_company_uuid:
            raise CompanyValidationError("No hay UUID principal de MATIAS configurado.")
        if not self.client.token:
            raise CompanyValidationError("No hay PAT válido configurado para MATIAS.")

    def record_attempt(self, *, company=None, operation, request_id=None, response=None, endpoint="", method="", successful=False, error_code="", error_message=""):
        values = {
            "company": company,
            "operation": operation,
            "http_method": method or (response or {}).get("method", ""),
            "endpoint": endpoint or (response or {}).get("endpoint", ""),
            "http_status": (response or {}).get("status_code") or None,
            "successful": successful,
            "error_code": error_code,
            "error_message": error_message or (response or {}).get("error", ""),
            "response_time_ms": (response or {}).get("response_time_ms"),
            "created_by": self.user if getattr(self.user, "is_authenticated", False) else None,
        }
        if request_id:
            attempt, _ = CompanySyncAttempt.objects.update_or_create(request_identifier=request_id, defaults=values)
            return attempt
        return CompanySyncAttempt.objects.create(request_identifier=None, **values)

    def find_remote_match(self, *, nit, email):
        response = self.client.list_companies()
        if not response["ok"]:
            return None, response
        for item in remote_records(response["data"]):
            remote = extract_remote_company(item)
            if (nit and remote["nit"] == nit) or (email and remote["email"] == email):
                return remote, response
        return None, response

    def update_link_from_remote(self, link, remote, *, status=CompanyProviderLink.STATUS_REGISTERED):
        link.parent_company_uuid = self.connection.parent_company_uuid
        link.matias_company_id = remote["id"] or link.matias_company_id
        link.matias_client_uuid = remote["client_uuid"] or link.matias_client_uuid
        link.remote_name = remote["name"] or link.remote_name
        link.remote_nit = remote["nit"] or link.remote_nit
        link.remote_email = remote["email"] or link.remote_email
        link.provider_status = status
        link.enabled_in_provider = remote["enabled"] or status == CompanyProviderLink.STATUS_REGISTERED
        link.last_sync_at = timezone.now()
        link.last_success_at = timezone.now()
        link.last_error_code = ""
        link.last_error_message = ""
        link.last_remote_snapshot = remote["raw"]
        link.save()
        return link

    @transaction.atomic
    def create_local_company(self, *, data, request_id):
        existing_request = CompanySyncAttempt.objects.filter(request_identifier=request_id, operation="CREATE", successful=True, company__isnull=False).first()
        if existing_request:
            return existing_request.company, existing_request.company.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment).first(), True

        nit = normalize_nit(data["nit"])
        email = normalize_email(data["email"])
        if Company.objects.filter(nit=nit, archived_at__isnull=True).exists():
            raise CompanyValidationError("Ya existe una empresa con este NIT.")
        if Company.objects.filter(email=email, archived_at__isnull=True).exists():
            raise CompanyValidationError("Ya existe una empresa con este correo.")
        company = Company.objects.create(
            legal_name=str(data["company_name"]).strip(),
            nit=nit,
            email=email,
            owner_first_name=str(data["first_name"]).strip(),
            owner_last_name=str(data["last_name"]).strip(),
            country_id=str(data["country_id"]),
            department_id=str(data.get("department_id") or ""),
            city_id=str(data["city_id"]),
            address=str(data["address"]).strip(),
            mobile=str(data["mobile"]).strip(),
            phone=str(data.get("phone") or "").strip(),
            local_status=Company.LOCAL_ACTIVE,
            onboarding_status=Company.ONBOARDING_COMPANY_REGISTERED,
            created_by=self.user if getattr(self.user, "is_authenticated", False) else None,
        )
        link = CompanyProviderLink.objects.create(company=company, provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment, parent_company_uuid=self.connection.parent_company_uuid, provider_status=CompanyProviderLink.STATUS_PENDING_CREATION)
        return company, link, False

    def create_company(self, *, data, request_id):
        self.ensure_ready()
        nit = normalize_nit(data["nit"])
        email = normalize_email(data["email"])
        remote, list_response = self.find_remote_match(nit=nit, email=email)
        if not list_response["ok"]:
            raise CompanyValidationError(list_response.get("error") or "No fue posible verificar empresas existentes en MATIAS antes de crear.")
        company, link, reused = self.create_local_company(data=data, request_id=request_id)
        if reused:
            return company
        if remote:
            self.update_link_from_remote(link, remote)
            self.record_attempt(company=company, operation="CREATE", request_id=request_id, response=list_response, successful=True)
            return company

        payload = {
            "first_name": company.owner_first_name,
            "last_name": company.owner_last_name,
            "company_name": company.legal_name,
            "email": company.email,
            "password": data["password"],
            "password_confirmation": data["password_confirmation"],
            "dni": company.nit,
            "country_id": data["country_id"],
            "city_id": data["city_id"],
            "address": company.address,
            "mobile": company.mobile,
            "phone": company.phone,
        }
        response = self.client.create_company(parent_uuid=self.connection.parent_company_uuid, payload=payload)
        success = response["ok"]
        self.record_attempt(company=company, operation="CREATE", request_id=request_id, response=response, method="POST", successful=success, error_code=str(response.get("status_code") or ""))
        if not success and response.get("error_type") != "TIMEOUT" and response.get("status_code") not in (500, 502, 503, 504):
            link.provider_status = CompanyProviderLink.STATUS_SYNC_ERROR
            link.last_error_code = str(response.get("status_code") or "MATIAS_ERROR")
            link.last_error_message = response.get("error") or "MATIAS rechazó la creación."
            link.save()
            raise CompanyValidationError(link.last_error_message)

        remote = self.recover_remote_company(nit=nit, email=email)
        if not remote:
            link.provider_status = CompanyProviderLink.STATUS_SYNC_ERROR
            link.last_sync_at = timezone.now()
            link.last_error_code = "REMOTE_NOT_FOUND_AFTER_CREATE"
            link.last_error_message = "La empresa local fue creada, pero MATIAS aún no devolvió ID o UUID. Use sincronizar para reconciliar."
            link.save()
            return company
        self.update_link_from_remote(link, remote)
        if link.matias_client_uuid:
            detail = self.client.get_company(client_uuid=link.matias_client_uuid)
            self.record_attempt(company=company, operation="VERIFY", response=detail, method="GET", successful=detail["ok"])
        write_audit_log(request=self.request, action="empresa_creada_matias", entity="Company", entity_id=company.id, status=AuditLog.STATUS_SUCCESS, message="Empresa creada y sincronizada con MATIAS.", metadata={"environment": self.connection.environment})
        return company

    def recover_remote_company(self, *, nit, email):
        for delay in (0, 0.5, 1):
            if delay:
                time.sleep(delay)
            remote, _ = self.find_remote_match(nit=nit, email=email)
            if remote:
                return remote
        return None

    def sync_company(self, company):
        self.ensure_ready()
        link, _ = CompanyProviderLink.objects.get_or_create(company=company, provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment)
        remote, response = self.find_remote_match(nit=company.nit, email=company.email)
        self.record_attempt(company=company, operation="SYNC", response=response, method="GET", successful=bool(remote))
        if not remote:
            link.provider_status = CompanyProviderLink.STATUS_REMOTE_NOT_FOUND if response["ok"] else CompanyProviderLink.STATUS_SYNC_ERROR
            link.last_sync_at = timezone.now()
            link.last_error_code = str(response.get("status_code") or "REMOTE_NOT_FOUND")
            link.last_error_message = response.get("error") or "La empresa no fue encontrada en MATIAS."
            link.save()
            return company
        self.update_link_from_remote(link, remote)
        return company

    def update_company(self, company, *, data):
        link = company.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment).first()
        if not link or not link.matias_company_id or not link.matias_client_uuid:
            raise CompanyValidationError("La empresa no tiene identificadores MATIAS completos para editar.")
        new_nit = normalize_nit(data.get("nit", company.nit))
        new_email = normalize_email(data.get("email", company.email))
        if Company.objects.filter(nit=new_nit, archived_at__isnull=True).exclude(id=company.id).exists():
            raise CompanyValidationError("Ya existe una empresa con este NIT.")
        if Company.objects.filter(email=new_email, archived_at__isnull=True).exclude(id=company.id).exists():
            raise CompanyValidationError("Ya existe una empresa con este correo.")
        previous = {"legal_name": company.legal_name, "nit": company.nit, "email": company.email}
        link.provider_status = CompanyProviderLink.STATUS_PENDING_UPDATE
        link.save(update_fields=["provider_status", "updated_at"])
        payload = {"name": str(data.get("company_name", company.legal_name)).strip(), "nit": new_nit, "email": new_email}
        response = self.client.update_company(company_id=link.matias_company_id, client_uuid=link.matias_client_uuid, payload=payload)
        self.record_attempt(company=company, operation="UPDATE", response=response, method="PUT", successful=response["ok"])
        if not response["ok"]:
            link.provider_status = CompanyProviderLink.STATUS_SYNC_ERROR
            link.last_error_code = str(response.get("status_code") or "MATIAS_ERROR")
            link.last_error_message = response.get("error") or "MATIAS rechazó la actualización."
            link.save()
            raise CompanyValidationError(link.last_error_message)
        company.legal_name = payload["name"]
        company.nit = new_nit
        company.email = new_email
        for field in ("owner_first_name", "owner_last_name", "department_id", "city_id", "country_id", "address", "mobile", "phone", "notes", "assigned_executive"):
            if field in data:
                setattr(company, field, str(data.get(field) or "").strip())
        company.save()
        detail = self.client.get_company(client_uuid=link.matias_client_uuid)
        remote = extract_remote_company(detail["data"]) if detail["ok"] else {"id": link.matias_company_id, "client_uuid": link.matias_client_uuid, "name": company.legal_name, "nit": company.nit, "email": company.email, "enabled": link.enabled_in_provider, "raw": {}}
        self.update_link_from_remote(link, remote)
        write_audit_log(request=self.request, action="empresa_actualizada_matias", entity="Company", entity_id=company.id, status=AuditLog.STATUS_SUCCESS, message="Empresa actualizada en NUVVI y MATIAS.", metadata={"previous": previous, "current": payload})
        return company

    def archive_company(self, company):
        company.local_status = Company.LOCAL_ARCHIVED
        company.archived_at = timezone.now()
        company.save(update_fields=["local_status", "archived_at", "updated_at"])
        write_audit_log(request=self.request, action="empresa_archivada", entity="Company", entity_id=company.id, status=AuditLog.STATUS_SUCCESS, message="Empresa archivada localmente.")
        return company

    def provider_action(self, company, *, action):
        link = company.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment).first()
        if not link or not link.matias_company_id:
            raise CompanyValidationError("La empresa no tiene ID MATIAS para ejecutar esta acción.")
        response = self.client.enable_company(company_id=link.matias_company_id) if action == "ENABLE" else self.client.disable_company(company_id=link.matias_company_id)
        self.record_attempt(company=company, operation=action, response=response, method="POST" if action == "ENABLE" else "DELETE", successful=response["ok"])
        if not response["ok"]:
            raise CompanyValidationError(response.get("error") or "MATIAS rechazó la acción solicitada.")
        link.provider_status = CompanyProviderLink.STATUS_REGISTERED if action == "ENABLE" else CompanyProviderLink.STATUS_REMOTE_DISABLED
        link.enabled_in_provider = action == "ENABLE"
        link.last_sync_at = timezone.now()
        link.last_success_at = timezone.now()
        link.last_error_code = ""
        link.last_error_message = ""
        link.last_remote_snapshot = sanitized_payload(response.get("data", {}))
        link.save()
        return company

    def stats(self, company):
        link = company.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment).first()
        if not link or not link.matias_client_uuid:
            raise CompanyValidationError("La empresa no tiene UUID MATIAS para consultar estadísticas.")
        response = self.client.get_company_stats(client_uuid=link.matias_client_uuid)
        self.record_attempt(company=company, operation="STATS", response=response, method="GET", successful=response["ok"])
        if not response["ok"]:
            raise CompanyValidationError(response.get("error") or "No se pudieron consultar estadísticas MATIAS.")
        return sanitized_payload(response["data"])

    def settings(self, company):
        link = company.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment).first()
        if not link or not link.matias_client_uuid:
            raise CompanyValidationError("La empresa no tiene UUID MATIAS para consultar configuración.")
        response = self.client.get_settings(client_uuid=link.matias_client_uuid)
        if not response["ok"]:
            raise CompanyValidationError(response.get("error") or "No se pudo consultar configuración MATIAS.")
        return sanitized_payload(response["data"])

    def update_setting(self, company, *, key, value):
        link = company.provider_links.filter(provider=CompanyProviderLink.PROVIDER_MATIAS, environment=self.connection.environment).first()
        if not link or not link.matias_client_uuid:
            raise CompanyValidationError("La empresa no tiene UUID MATIAS para actualizar configuración.")
        response = self.client.update_setting(client_uuid=link.matias_client_uuid, key=key, value=value)
        self.record_attempt(company=company, operation="SETTING", response=response, method="PUT", successful=response["ok"])
        if not response["ok"]:
            raise CompanyValidationError(response.get("error") or "No se pudo actualizar configuración MATIAS.")
        return sanitized_payload(response["data"])


def search_companies(queryset, params):
    search = str(params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(Q(legal_name__icontains=search) | Q(nit__icontains=search) | Q(email__icontains=search))
    if params.get("local_status"):
        queryset = queryset.filter(local_status=params["local_status"])
    if params.get("onboarding_status"):
        queryset = queryset.filter(onboarding_status=params["onboarding_status"])
    if params.get("environment"):
        queryset = queryset.filter(provider_links__environment=params["environment"])
    if params.get("provider_status"):
        queryset = queryset.filter(provider_links__provider_status=params["provider_status"])
    return queryset.distinct()
