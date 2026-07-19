import hashlib
import json
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.html import escape
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .models import User
from .serializers import AdminUserSerializer, PasswordChangeSerializer, PasswordSetupSerializer, ProfileUpdateSerializer, UserSerializer
from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _load_colombia_locations():
    data_path = Path(__file__).resolve().parent / "data" / "colombia_locations.json"
    with data_path.open(encoding="utf-8-sig") as data_file:
        return json.load(data_file)


def _send_admin_invitation(user: User, token: str) -> None:
    setup_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/crear-contrasena/{token}"
    role_label = user.get_admin_role_display() if user.admin_role else "Superadministrador"
    created_at = timezone.localtime(user.created_at).strftime("%d/%m/%Y %I:%M %p")
    subject = "Nueva cuenta administrativa en Nuvvi"
    text_message = (
        f"Hola {user.full_name},\n\n"
        f"Se creó tu cuenta administrativa en Nuvvi con rol {role_label}.\n"
        f"Crea tu contraseña desde este enlace seguro: {setup_url}\n"
    )
    html_message = f"""
    <div style="margin:0;padding:0;background:#F8FCFF;font-family:Arial,Helvetica,sans-serif;color:#102F4B;">
      <div style="max-width:640px;margin:0 auto;padding:32px 18px;">
        <div style="background:#ffffff;border:1px solid #D9ECFA;border-radius:28px;overflow:hidden;box-shadow:0 18px 50px rgba(79,159,240,.16);">
          <div style="background:linear-gradient(135deg,#0C1E33,#246FC1);padding:30px;text-align:center;color:#fff;">
            <img src="{settings.FRONTEND_BASE_URL.rstrip('/')}/logo-favicon-nuvvi.png" alt="Nuvvi" style="width:84px;height:84px;object-fit:contain;margin-bottom:12px;" />
            <h1 style="margin:0;font-size:26px;letter-spacing:.04em;">Bienvenido a Nuvvi</h1>
            <p style="margin:8px 0 0;color:#D9ECFA;font-size:14px;">Nueva cuenta administrativa creada</p>
          </div>
          <div style="padding:30px;">
            <p style="font-size:17px;margin:0 0 12px;">Hola <strong>{escape(user.full_name)}</strong>,</p>
            <p style="font-size:14px;line-height:1.7;color:#39566F;margin:0 0 22px;">Tu cuenta fue creada desde la sección administrativa de Nuvvi. Para proteger el acceso, debes crear tu contraseña usando el enlace seguro de un solo uso.</p>
            <div style="background:#F8FCFF;border:1px solid #D9ECFA;border-radius:18px;padding:18px;margin:0 0 24px;">
              <p style="margin:0 0 8px;font-size:13px;color:#6C8398;"><strong>Correo:</strong> {escape(user.email)}</p>
              <p style="margin:0 0 8px;font-size:13px;color:#6C8398;"><strong>Rol:</strong> {escape(role_label)}</p>
              <p style="margin:0;font-size:13px;color:#6C8398;"><strong>Fecha de creación:</strong> {created_at}</p>
            </div>
            <div style="text-align:center;margin:28px 0;">
              <a href="{setup_url}" style="display:inline-block;background:#4F9FF0;color:#fff;text-decoration:none;font-weight:700;padding:14px 24px;border-radius:14px;box-shadow:0 10px 26px rgba(79,159,240,.28);">Crear mi contraseña</a>
            </div>
            <p style="font-size:12px;line-height:1.6;color:#6C8398;margin:0;">Si no reconoces esta invitación, ignora este correo. Por seguridad, el enlace es único, largo y expira automáticamente.</p>
          </div>
        </div>
      </div>
    </div>
    """
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message, fail_silently=False)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.admin_role == User.ROLE_SUPERADMIN))


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        write_audit_log(
            request=request,
            action="perfil_actualizado",
            entity="accounts.User",
            entity_id=user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario actualizó su perfil personal.",
            metadata={"email": user.email, "username": user.username},
        )
        return Response(UserSerializer(user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        write_audit_log(
            request=request,
            action="perfil_actualizado",
            entity="accounts.User",
            entity_id=user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario actualizó parcialmente su perfil personal.",
            metadata={"email": user.email, "username": user.username},
        )
        return Response(UserSerializer(user).data)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password"])
        request.user.save(update_fields=["password", "updated_at"])

        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)

        write_audit_log(
            request=request,
            action="contrasena_actualizada",
            entity="accounts.User",
            entity_id=request.user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario cambió su contraseña y se invalidaron sus sesiones.",
        )

        return Response({"detail": "Contraseña actualizada correctamente. Inicia sesión nuevamente."})


class ColombiaLocationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_load_colombia_locations())


class AdminUserViewSet(viewsets.ModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsSuperAdmin]
    search_fields = ["email", "full_name", "identification_number", "admin_role"]
    ordering_fields = ["created_at", "last_login", "full_name", "email"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return User.objects.filter(is_staff=True).order_by("-created_at")

    def perform_create(self, serializer):
        user = serializer.save()
        write_audit_log(
            request=self.request,
            action="usuario_creado",
            entity="accounts.User",
            entity_id=user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario administrativo creado.",
            metadata={"email": user.email, "username": user.username, "role": user.admin_role},
        )
        self._issue_invitation(user)

    def perform_update(self, serializer):
        user = serializer.save()
        write_audit_log(
            request=self.request,
            action="usuario_actualizado",
            entity="accounts.User",
            entity_id=user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario administrativo actualizado.",
            metadata={"email": user.email, "username": user.username, "role": user.admin_role},
        )

    def perform_destroy(self, instance):
        metadata = {"email": instance.email, "username": instance.username, "identification_number": instance.identification_number}
        entity_id = instance.id
        instance.delete()
        write_audit_log(
            request=self.request,
            action="usuario_eliminado",
            entity="accounts.User",
            entity_id=entity_id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario administrativo eliminado.",
            metadata=metadata,
        )

    @action(detail=True, methods=["post"], url_path="resend-invitation")
    def resend_invitation(self, request, pk=None):
        user = self.get_object()
        self._issue_invitation(user)
        return Response(AdminUserSerializer(user).data)

    def _issue_invitation(self, user: User):
        token = secrets.token_urlsafe(48)
        user.password_setup_token_hash = _hash_token(token)
        user.password_setup_expires_at = timezone.now() + timedelta(days=7)
        user.password_setup_used_at = None
        user.invitation_sent_at = timezone.now()
        user.save(update_fields=["password_setup_token_hash", "password_setup_expires_at", "password_setup_used_at", "invitation_sent_at", "updated_at"])
        try:
            _send_admin_invitation(user, token)
            write_audit_log(
                request=self.request,
                action="correo_invitacion_enviado",
                entity="accounts.User",
                entity_id=user.id,
                status=AuditLog.STATUS_SUCCESS,
                message="Correo de invitación enviado correctamente.",
                metadata={"email": user.email, "username": user.username},
            )
        except Exception as exc:
            write_audit_log(
                request=self.request,
                action="correo_invitacion_fallido",
                entity="accounts.User",
                entity_id=user.id,
                status=AuditLog.STATUS_ERROR,
                message="No se pudo enviar el correo de invitación.",
                error_message=str(exc),
                metadata={"email": user.email, "username": user.username},
            )
            raise


class PasswordSetupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_user(self, token: str):
        token_hash = _hash_token(token)
        return User.objects.filter(
            password_setup_token_hash=token_hash,
            password_setup_used_at__isnull=True,
            password_setup_expires_at__gt=timezone.now(),
            is_staff=True,
        ).first()

    def get(self, request, token):
        user = self.get_user(token)
        if not user:
            return Response({"detail": "El enlace no es válido o expiró."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"full_name": user.full_name, "email": user.email})

    def post(self, request, token):
        user = self.get_user(token)
        if not user:
            return Response({"detail": "El enlace no es válido o expiró."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PasswordSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.password_setup_used_at = timezone.now()
        user.password_setup_token_hash = ""
        user.is_active = True
        user.save(update_fields=["password", "password_setup_used_at", "password_setup_token_hash", "is_active", "updated_at"])
        write_audit_log(
            request=request,
            actor=user,
            action="contrasena_invitacion_creada",
            entity="accounts.User",
            entity_id=user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Usuario creó contraseña desde enlace de invitación.",
        )
        return Response({"detail": "Contraseña creada correctamente."})
