from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dian.models import MatiasConnection
from apps.dian.views import IsSuperAdmin
from apps.accounts.models import User

from .models import Company, CompanySyncAttempt
from .serializers import CompanyCreateSerializer, CompanySerializer, CompanySettingSerializer, CompanyUpdateSerializer, fetch_catalogs
from .services import CompanyApplicationService, CompanyValidationError, normalize_email, normalize_nit, search_companies


def environment_from_request(request):
    value = request.data.get("environment") if hasattr(request, "data") else None
    value = value or request.query_params.get("environment")
    return value if value in dict(MatiasConnection.ENVIRONMENT_CHOICES) else MatiasConnection.ENVIRONMENT_SANDBOX


def validation_error_response(exc):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


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
