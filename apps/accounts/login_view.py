import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .rate_limiter import LoginRateLimiter
from .serializers import UserSerializer
from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log

logger = logging.getLogger("django")


def _get_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class LoginView(APIView):
    """Login seguro con rate limiting por correo, usuario o identificación."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        credential = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        client_ip = self._get_client_ip(request)

        if not credential or not password:
            return Response(
                {"detail": "Correo, usuario o identificación y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limiter = LoginRateLimiter(request, credential)

        if limiter.is_blocked():
            remaining = limiter.get_remaining_lockout()
            logger.warning(
                f"SECURITY: Login blocked for '{credential}' from {client_ip}. "
                f"Lockout remaining: {remaining}s"
            )
            write_audit_log(
                request=request,
                action="login_bloqueado",
                entity="auth",
                status=AuditLog.STATUS_WARNING,
                message="Inicio de sesión bloqueado por demasiados intentos.",
                metadata={"credential": credential, "retry_after_seconds": remaining},
            )
            return Response(
                {
                    "detail": "Demasiados intentos. Intenta de nuevo más tarde.",
                    "retry_after_seconds": remaining,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        limiter.increment()

        from django.contrib.auth import authenticate
        user = authenticate(request, username=credential, password=password)

        if user is None or not user.is_active:
            logger.warning(
                f"SECURITY: Failed login attempt for '{credential}' from {client_ip}"
            )
            write_audit_log(
                request=request,
                action="login_fallido",
                entity="auth",
                status=AuditLog.STATUS_ERROR,
                message="Intento de inicio de sesión fallido.",
                error_message="Usuario inactivo o credenciales incorrectas.",
                metadata={"credential": credential},
            )
            return Response(
                {"detail": "Usuario o contraseña incorrecto."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        limiter.reset()
        user.last_login = timezone.now()
        user.save(update_fields=["last_login", "updated_at"])
        tokens = _get_tokens_for_user(user)
        user_data = UserSerializer(user).data

        logger.info(
            f"SECURITY: Successful login for '{user.email}' (id={user.id}, "
            f"is_staff={user.is_staff}, is_superuser={user.is_superuser}) from {client_ip}"
        )
        write_audit_log(
            request=request,
            actor=user,
            action="login_exitoso",
            entity="auth",
            entity_id=user.id,
            status=AuditLog.STATUS_SUCCESS,
            message="Inicio de sesión exitoso.",
            metadata={"credential": credential},
        )

        return Response(
            {"access": tokens["access"], "refresh": tokens["refresh"], "user": user_data},
            status=status.HTTP_200_OK,
        )

    def _get_client_ip(self, request) -> str:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
