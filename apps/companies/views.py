from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dian.models import MatiasConnection
from apps.dian.views import IsSuperAdmin

from .models import Company
from .serializers import CompanyCreateSerializer, CompanySerializer, CompanySettingSerializer, CompanyUpdateSerializer, fetch_catalogs
from .services import CompanyApplicationService, CompanyValidationError, search_companies


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
        company = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request)).archive_company(get_object_or_404(Company, pk=pk))
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


class CompanyReconcileView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        service = CompanyApplicationService(user=request.user, request=request, environment=environment_from_request(request))
        updated = 0
        errors = 0
        for company in Company.objects.filter(archived_at__isnull=True):
            try:
                service.sync_company(company)
                updated += 1
            except CompanyValidationError:
                errors += 1
        return Response({"updated": updated, "errors": errors})


class CompanyCatalogsView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(fetch_catalogs(environment_from_request(request)))
