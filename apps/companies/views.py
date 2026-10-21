import re
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dian.models import MatiasConnection
from apps.dian.matias_service import get_connection
from apps.dian.views import IsSuperAdmin
from apps.accounts.models import User

from .models import Company, CompanySyncAttempt
from .serializers import CompanyCreateSerializer, CompanySerializer, CompanySettingSerializer, CompanyUpdateSerializer, fetch_catalogs
from .services import CompanyApplicationService, CompanyValidationError, MatiasCompanyClient, normalize_email, normalize_nit, search_companies


def environment_from_request(request):
    value = request.data.get("environment") if hasattr(request, "data") else None
    value = value or request.query_params.get("environment")
    return value if value in dict(MatiasConnection.ENVIRONMENT_CHOICES) else MatiasConnection.ENVIRONMENT_SANDBOX


def validation_error_response(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def sanitize_provider_data(value):
    """Mask secrets without truncating provider lists or hiding useful metadata."""
    sensitive = ("token", "authorization", "password", "passphrase", "private_key", "secret", "base64certificate", "certificate_data", "certificate_file", "p12", "pfx")
    if isinstance(value, dict):
        return {key: "***" if any(part in str(key).lower() for part in sensitive) else sanitize_provider_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_provider_data(item) for item in value]
    return value


class CompanyListCreateView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        queryset = search_companies(Company.objects.filter(archived_at__isnull=True).prefetch_related("provider_links", "sync_attempts"), request.query_params)
        return Response(CompanySerializer(queryset, many=True, context={"environment": environment_from_request(request)}).data)

    def post(self, request):
        serializer = CompanyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            service = CompanyApplicationService(user=request.user, request=request, environment=serializer.validated_data["environment"])
            company = service.create_company(data=serializer.validated_data, request_id=serializer.validated_data["request_id"])
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(CompanySerializer(company, context={"environment": serializer.validated_data["environment"]}).data, status=status.HTTP_201_CREATED)


class CompanyDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def get_object(self, pk):
        return get_object_or_404(Company.objects.prefetch_related("provider_links", "sync_attempts"), pk=pk)

    def get(self, request, pk):
        return Response(CompanySerializer(self.get_object(pk), context={"environment": environment_from_request(request)}).data)

    def patch(self, request, pk):
        serializer = CompanyUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            service = CompanyApplicationService(user=request.user, request=request, environment=serializer.validated_data.get("environment"))
            company = service.update_company(self.get_object(pk), data=serializer.validated_data)
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(CompanySerializer(company, context={"environment": serializer.validated_data.get("environment", MatiasConnection.ENVIRONMENT_SANDBOX)}).data)


class CompanySyncView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        try:
            service = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request))
            company = service.sync_company(get_object_or_404(Company, pk=pk))
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(CompanySerializer(company, context={"environment": environment_from_request(request)}).data)


class CompanyEnableProviderView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        try:
            company = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request)).provider_action(get_object_or_404(Company, pk=pk), action="ENABLE")
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(CompanySerializer(company, context={"environment": environment_from_request(request)}).data)


class CompanyDisableProviderView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        try:
            company = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request)).provider_action(get_object_or_404(Company, pk=pk), action="DISABLE")
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(CompanySerializer(company, context={"environment": environment_from_request(request)}).data)


class CompanyArchiveView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        try:
            company = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request)).archive_company(get_object_or_404(Company, pk=pk))
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(CompanySerializer(company, context={"environment": environment_from_request(request)}).data)


class CompanyStatsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        try:
            data = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request)).stats(get_object_or_404(Company, pk=pk))
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(data)


class CompanySettingsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        try:
            data = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request)).settings(get_object_or_404(Company, pk=pk))
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(data)

    def put(self, request, pk):
        serializer = CompanySettingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = CompanyApplicationService(user=request.user, request=request, environment=serializer.validated_data["environment"]).update_setting(get_object_or_404(Company, pk=pk), key=serializer.validated_data["setting_key"], value=serializer.validated_data["setting_value"])
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(data)


class CompanyDianConfigurationView(APIView):
    """Narrow proxy for documented MATIAS per-customer DIAN setup endpoints."""
    permission_classes = [IsSuperAdmin]
    resources = {"software", "resolutions", "numbering-range", "certificate"}

    def dispatch_matias(self, request, company, resource):
        environment = environment_from_request(request)
        link = company.provider_links.filter(provider="MATIAS", environment=environment).first()
        if not link or not link.matias_client_uuid or not link.enabled_in_provider:
            return Response({"detail": "La empresa debe estar registrada y habilitada en MATIAS para este ambiente."}, status=400)
        client = MatiasCompanyClient(get_connection(environment))
        if resource not in self.resources:
            return Response({"detail": "Recurso DIAN no permitido."}, status=400)
        params = {"client_uuid": link.matias_client_uuid}
        if resource == "numbering-range":
            params.update({k: v for k, v in request.query_params.items() if k in {"type_id", "sync"}})
        elif resource == "software":
            params.update({k: v for k, v in request.query_params.items() if k == "uid"})
        body = request.data if isinstance(request.data, dict) else {}
        item_id = body.get("id") or request.query_params.get("id")
        action = body.get("action") or request.query_params.get("action")
        if item_id and not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(item_id)):
            return Response({"detail": "El identificador de MATIAS no es válido."}, status=400)
        if resource == "software" and action == "run-test" and not str(body.get("software_id", "")).isdigit():
            return Response({"detail": "software_id debe ser el identificador numérico de un software DIAN."}, status=400)
        if resource == "software" and action == "run-test":
            endpoint, method = "/document/run-test", "POST"
            payload = {"software_id": body.get("software_id")}
        elif resource == "software" and action == "test-set":
            endpoint, method, payload = f"/software/test/{item_id}", "GET", None
        elif resource == "certificate" and action in {"upload", "renew"}:
            if action == "renew" and not item_id:
                return Response({"detail": "El ID del certificado activo es obligatorio para renovarlo."}, status=400)
            endpoint = f"/certificate/{item_id}" if action == "renew" else "/certificate"
            method = "PUT" if action == "renew" else "POST"
            payload = {key: body[key] for key in ("certificate", "password", "description") if key in body}
            if not payload.get("certificate") or not payload.get("password"):
                return Response({"detail": "Selecciona el certificado .p12/.pfx e ingresa su contraseña."}, status=400)
            if not isinstance(payload["certificate"], str) or not payload["certificate"].startswith("data:application/x-pkcs12;base64,"):
                return Response({"detail": "El certificado debe enviarse codificado como PKCS#12 (.p12/.pfx)."}, status=400)
            if len(payload["certificate"]) > 2_100_000:
                return Response({"detail": "El certificado supera el tamaño máximo permitido de 1,5 MB."}, status=400)
        elif resource == "certificate" and action == "expiration":
            dni = body.get("dni") or company.nit
            endpoint, method, payload = f"/certificate/expiration/{dni}", "GET", None
        else:
            suffix = f"/{item_id}" if item_id else ""
            method = request.method
            endpoint = f"/{resource}{suffix}"
            payload = {key: value for key, value in body.items() if key not in {"environment", "action", "id", "resource"}}
        response = client._request(f"{endpoint}?{urlencode(params)}", method=method, payload=payload)
        CompanySyncAttempt.objects.create(
            company=company, operation=f"DIAN_{action or method}_{resource}"[:40],
            http_method=method, endpoint=endpoint, http_status=response.get("status_code") or None,
            successful=response["ok"], error_code=str(response.get("error_type") or "")[:50],
            error_message=(response.get("error") or "")[:2000],
            response_time_ms=response.get("response_time_ms"), created_by=request.user,
        )
        if not response["ok"]:
            return Response({"detail": response.get("error") or "MATIAS rechazó la solicitud.", "provider": sanitize_provider_data(response.get("data", {}))}, status=response.get("status_code") or 502)
        return Response(sanitize_provider_data(response.get("data", {})), status=response.get("status_code") or 200)

    def get(self, request, pk):
        resource = request.query_params.get("resource", "")
        return self.dispatch_matias(request, get_object_or_404(Company, pk=pk), resource)

    def post(self, request, pk):
        return self.dispatch_matias(request, get_object_or_404(Company, pk=pk), str(request.data.get("resource", "")))

    def put(self, request, pk):
        return self.dispatch_matias(request, get_object_or_404(Company, pk=pk), str(request.data.get("resource", "")))

    def delete(self, request, pk):
        return self.dispatch_matias(request, get_object_or_404(Company, pk=pk), request.query_params.get("resource", ""))


class CompanyProviderSyncStatusView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        connection = MatiasConnection.objects.filter(environment=environment_from_request(request)).first()
        return Response({
            "environment": environment_from_request(request),
            "connection_status": connection.connection_status if connection else "NOT_CONFIGURED",
            "operational_status": connection.operational_status if connection else "PAT_REQUIRED",
            "linked_companies_count": connection.linked_companies_count if connection else 0,
            "ready": bool(connection and connection.operational_status == MatiasConnection.OP_READY),
        })


class CompanyIdentityCheckView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        environment = environment_from_request(request)
        nit = normalize_nit(request.query_params.get("nit"))
        email = normalize_email(request.query_params.get("email"))
        retry_id = str(request.query_params.get("request_id") or "")
        retry_attempt = CompanySyncAttempt.objects.filter(request_identifier=retry_id, operation="CREATE", company__isnull=False).select_related("company").first() if retry_id else None
        retry_company = retry_attempt.company if retry_attempt and retry_attempt.company.environment == environment and retry_attempt.company.nit == nit and retry_attempt.company.email.lower() == email else None
        companies_by_nit = Company.objects.filter(environment=environment, nit=nit) if nit else Company.objects.none()
        companies_by_email = Company.objects.filter(environment=environment, email__iexact=email) if email else Company.objects.none()
        users_by_email = User.objects.filter(email__iexact=email) if email else User.objects.none()
        if retry_company:
            companies_by_nit = companies_by_nit.exclude(pk=retry_company.pk)
            companies_by_email = companies_by_email.exclude(pk=retry_company.pk)
            if retry_company.owner_user_id:
                users_by_email = users_by_email.exclude(pk=retry_company.owner_user_id)
        nit_exists = bool(nit and companies_by_nit.exists())
        email_exists = bool(email and (companies_by_email.exists() or users_by_email.exists()))
        return Response({"nit_exists": nit_exists, "email_exists": email_exists})


class CompanyReconcileView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        service = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request))
        try:
            service.ensure_ready()
            result = service.synchronize_remote_companies()
        except CompanyValidationError as exc:
            return validation_error_response(exc)
        return Response(result)


class CompanyCatalogsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(fetch_catalogs(environment_from_request(request)))
