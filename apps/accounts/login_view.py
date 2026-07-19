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

logger = logging.getLogger("django")


def _get_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class LoginView(APIView):
    """Login seguro con rate limiting, respeta el backend EmailOrUsernameBackend."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email_or_username = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        client_ip = self._get_client_ip(request)

        if not email_or_username or not password:
            return Response(
                {"detail": "Email/usuario y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limiter = LoginRateLimiter(request, email_or_username)

        if limiter.is_blocked():
            remaining = limiter.get_remaining_lockout()
            logger.warning(
                f"SECURITY: Login blocked for '{email_or_username}' from {client_ip}. "
                f"Lockout remaining: {remaining}s"
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
        user = authenticate(request, username=email_or_username, password=password)

        if user is None or not user.is_active:
            logger.warning(
                f"SECURITY: Failed login attempt for '{email_or_username}' from {client_ip}"
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

        return Response(
            {"access": tokens["access"], "refresh": tokens["refresh"], "user": user_data},
            status=status.HTTP_200_OK,
        )

    def _get_client_ip(self, request) -> str:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")
