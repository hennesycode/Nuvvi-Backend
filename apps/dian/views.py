from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log

from .matias_service import CATALOG_ENDPOINTS, generate_pat, get_connection, is_token_expired, revoke_current_pat, run_connection_test, store_validated_pat, sync_catalogs
from .models import MatiasConnection
from .serializers import MatiasConnectionSerializer, MatiasGeneratePatSerializer, MatiasTokenSerializer


def safe_errors(serializer):
    errors = dict(serializer.errors)
    errors.pop("access_token", None)
    errors.pop("password", None)
    return errors


def apply_local_status(connection):
    if not connection.enabled:
        connection.connection_status = MatiasConnection.STATUS_DISABLED
        connection.operational_status = MatiasConnection.OP_INACTIVE
    elif not connection.encrypted_access_token:
        connection.connection_status = MatiasConnection.STATUS_NOT_CONFIGURED
        connection.operational_status = MatiasConnection.OP_PAT_REQUIRED
    elif is_token_expired(connection):
        connection.connection_status = MatiasConnection.STATUS_AUTHENTICATION_ERROR
        connection.operational_status = MatiasConnection.OP_TOKEN_EXPIRED
    elif connection.connection_status in (
        MatiasConnection.STATUS_DISABLED,
        MatiasConnection.STATUS_NOT_CONFIGURED,
        MatiasConnection.STATUS_AUTHENTICATION_ERROR,
    ):
        connection.connection_status = MatiasConnection.STATUS_DISCONNECTED
        connection.operational_status = MatiasConnection.OP_CATALOGS_NOT_SYNCED


def request_environment(request):
    value = request.data.get("environment") if hasattr(request, "data") else None
    value = value or request.query_params.get("environment")
    return value if value in dict(MatiasConnection.ENVIRONMENT_CHOICES) else MatiasConnection.ENVIRONMENT_SANDBOX


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.admin_role == "superadmin"))


class MatiasConnectionView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(MatiasConnectionSerializer(get_connection(request_environment(request))).data)

    def put(self, request):
        connection = get_connection(request_environment(request))
        previous_environment = connection.environment
        serializer = MatiasConnectionSerializer(connection, data=request.data, partial=True)
        if not serializer.is_valid():
            write_audit_log(
                request=request,
                action="matias_configuracion_error",
                entity="MatiasConnection",
                entity_id=connection.id,
                status=AuditLog.STATUS_ERROR,
                message="No se pudo guardar la configuración de MATIAS.",
                error_message=str(safe_errors(serializer)),
                metadata={"environment": request.data.get("environment"), "enabled": request.data.get("enabled")},
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        updated = serializer.save(updated_by=request.user, created_by=connection.created_by or request.user)
        apply_local_status(updated)
        updated.save()
        write_audit_log(
            request=request,
            action="matias_configuracion_guardada",
            entity="MatiasConnection",
            entity_id=updated.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Configuración de MATIAS actualizada.",
            metadata={"environment": updated.environment, "previous_environment": previous_environment, "enabled": updated.enabled},
        )
        return Response(MatiasConnectionSerializer(updated).data)


class MatiasTokenView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = get_connection(request_environment(request))
        serializer = MatiasTokenSerializer(data=request.data)
        if not serializer.is_valid():
            write_audit_log(
                request=request,
                action="matias_pat_error",
                entity="MatiasConnection",
                entity_id=connection.id,
                status=AuditLog.STATUS_ERROR,
                message="No se pudo guardar el PAT de MATIAS.",
                error_message=str(safe_errors(serializer)),
                metadata={"token_name": request.data.get("token_name"), "account_email": request.data.get("account_email")},
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            connection = store_validated_pat(
                connection,
                serializer.validated_data["access_token"],
                token_name=serializer.validated_data.get("token_name", connection.token_name),
                account_email=serializer.validated_data.get("account_email", connection.account_email),
                request=request,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        connection.updated_by = request.user
        connection.created_by = connection.created_by or request.user
        connection.save()
        write_audit_log(request=request, action="matias_pat_guardado", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_SUCCESS, message="PAT de MATIAS validado y guardado cifrado.", metadata={"token_name": connection.token_name, "account_email": connection.account_email, "environment": connection.environment})
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasGeneratePatView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = get_connection(request_environment(request))
        serializer = MatiasGeneratePatSerializer(data=request.data)
        if not serializer.is_valid():
            write_audit_log(
                request=request,
                action="matias_pat_generacion_error",
                entity="MatiasConnection",
                entity_id=connection.id,
                status=AuditLog.STATUS_ERROR,
                message="Solicitud inválida para generar PAT de MATIAS.",
                error_message=str(safe_errors(serializer)),
                metadata={"email": request.data.get("email"), "token_name": request.data.get("token_name")},
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            connection = generate_pat(connection, request=request, **serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasTestView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = run_connection_test(get_connection(request_environment(request)), request=request)
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasSyncCatalogsView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = sync_catalogs(get_connection(request_environment(request)), request=request)
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasCatalogDataView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        connection = get_connection(request_environment(request))
        catalog_key = request.query_params.get("catalog")
        catalog_endpoints = {f"/{endpoint}" for endpoint, _ in CATALOG_ENDPOINTS}
        if catalog_key:
            endpoint = f"/{catalog_key.strip('/')}"
            if endpoint not in catalog_endpoints:
                return Response({"detail": "Catálogo MATIAS no reconocido."}, status=status.HTTP_404_NOT_FOUND)
            sync = connection.catalog_syncs.filter(endpoint=endpoint).first()
            if not sync or not sync.catalog_data or not sync.last_success_at:
                return Response({"detail": "El catálogo aún no está sincronizado correctamente."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"environment": connection.environment, "endpoint": endpoint, "name": sync.catalog_name, "status": sync.status, "error_message": sync.error_message, "records_count": len(sync.catalog_data), "last_synced_at": sync.last_success_at, "results": sync.catalog_data})

        syncs = {item.endpoint: item for item in connection.catalog_syncs.all()}
        return Response({
            "environment": connection.environment,
            "results": [
                {
                    "key": endpoint,
                    "endpoint": f"/{endpoint}",
                    "name": label,
                    "status": syncs[f"/{endpoint}"].status if f"/{endpoint}" in syncs else MatiasConnection.CATALOGS_PENDING,
                    "records_count": syncs[f"/{endpoint}"].records_count if f"/{endpoint}" in syncs else None,
                    "last_synced_at": syncs[f"/{endpoint}"].last_success_at if f"/{endpoint}" in syncs else None,
                }
                for endpoint, label in CATALOG_ENDPOINTS
            ],
        })


class MatiasRevokeTokenView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            connection = revoke_current_pat(get_connection(request_environment(request)), request=request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MatiasConnectionSerializer(connection).data)
