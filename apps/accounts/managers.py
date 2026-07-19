from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def _build_username(self, email):
        base = (email.split("@")[0] if email else "usuario").lower()
        base = "".join(char for char in base if char.isalnum() or char in "._-").strip("._-") or "usuario"
        username = base[:150]
        suffix = 1
        while self.model.objects.filter(username__iexact=username).exists():
            ending = f"-{suffix}"
            username = f"{base[:150 - len(ending)]}{ending}"
            suffix += 1
        return username

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", self._build_username(email))
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)
