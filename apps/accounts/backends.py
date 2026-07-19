from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User


class EmailOrUsernameBackend(ModelBackend):
    """Autentica por email exacto o por alias sin dominio (ej: 'admin' -> 'admin@*')."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        username = username.strip().lower()

        if "@" in username:
            lookup = Q(email__iexact=username)
        else:
            lookup = Q(email__istartswith=f"{username}@")

        try:
            user = User.objects.get(lookup)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(lookup).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
