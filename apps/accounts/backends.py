from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class EmailOrUsernameBackend(ModelBackend):
    """Autentica por email, username, identificación o alias sin dominio."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        credential = username.strip().lower()

        exact_lookup = Q(email__iexact=credential) | Q(username__iexact=credential)
        if credential.isdigit():
            exact_lookup |= Q(identification_number=credential)

        user = User.objects.filter(exact_lookup).first()

        if user is None and "@" not in credential:
            # Mantiene compatibilidad con el acceso tipo "admin" -> "admin@...".
            user = User.objects.filter(email__istartswith=f"{credential}@").order_by("id").first()

        if user is None:
            User().set_password(password)
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
