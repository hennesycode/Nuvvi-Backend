from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log

from .matias_service import encrypt_secret, generate_pat, get_connection, run_connection_test, sync_catalogs
from .serializers import MatiasConnectionSerializer, MatiasGeneratePatSerializer, MatiasTokenSerializer


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.admin_role == "superadmin"))


class MatiasConnectionView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(MatiasConnectionSerializer(get_connection()).data)

    def put(self, request):
        connection = get_connection()
        previous_environment = connection.environment
        serializer = MatiasConnectionSerializer(connection, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save(updated_by=request.user, created_by=connection.created_by or request.user)
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
        connection = get_connection()
        serializer = MatiasTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        connection.encrypted_access_token = encrypt_secret(serializer.validated_data["access_token"])
        connection.token_name = serializer.validated_data.get("token_name", connection.token_name)
        connection.token_external_id = serializer.validated_data.get("token_external_id", connection.token_external_id)
        connection.token_expires_at = serializer.validated_data.get("token_expires_at", connection.token_expires_at)
        connection.account_email = serializer.validated_data.get("account_email", connection.account_email)
        connection.updated_by = request.user
        if not connection.created_by:
            connection.created_by = request.user
        connection.save()
        write_audit_log(request=request, action="matias_pat_guardado", entity="MatiasConnection", entity_id=connection.id, status=AuditLog.STATUS_SUCCESS, message="PAT de MATIAS guardado cifrado.", metadata={"token_name": connection.token_name, "account_email": connection.account_email})
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasGeneratePatView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = get_connection()
        serializer = MatiasGeneratePatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            connection = generate_pat(connection, request=request, **serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasTestView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = run_connection_test(get_connection(), request=request)
        return Response(MatiasConnectionSerializer(connection).data)


class MatiasSyncCatalogsView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        connection = sync_catalogs(get_connection(), request=request)
        return Response(MatiasConnectionSerializer(connection).data)
