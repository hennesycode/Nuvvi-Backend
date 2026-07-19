import hashlib
import time
from django.core.cache import cache
from django.conf import settings


class LoginRateLimiter:
    """Rate limiter for login attempts per IP / per username."""

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 900  # 15 minutes
    LOCKOUT_SECONDS = 1800  # 30 minutes if exceeded

    def __init__(self, request, username: str):
        self.request = request
        self.username = username.lower().strip()
        self.client_ip = self._get_client_ip()
        self._ip_key = f"login_rate:ip:{self.client_ip}"
        self._user_key = f"login_rate:user:{hashlib.sha256(self.username.encode()).hexdigest()[:16]}"
        self._lockout_key = f"login_lockout:ip:{self.client_ip}"

    def _get_client_ip(self) -> str:
        x_forwarded = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return self.request.META.get("REMOTE_ADDR", "0.0.0.0")

    def is_blocked(self) -> bool:
        return cache.get(self._lockout_key) is not None

    def increment(self) -> dict:
        timestamp = time.time()
        cache.set(self._ip_key, cache.get(self._ip_key, 0) + 1, timeout=self.WINDOW_SECONDS)
        cache.set(self._user_key, cache.get(self._user_key, 0) + 1, timeout=self.WINDOW_SECONDS)

        ip_count = cache.get(self._ip_key, 0)
        user_count = cache.get(self._user_key, 0)

        if ip_count > self.MAX_ATTEMPTS or user_count > self.MAX_ATTEMPTS:
            cache.set(self._lockout_key, time.time(), timeout=self.LOCKOUT_SECONDS)

        return {
            "ip_attempts": ip_count,
            "user_attempts": user_count,
            "max_attempts": self.MAX_ATTEMPTS,
            "window_seconds": self.WINDOW_SECONDS,
        }

    def reset(self):
        cache.delete(self._ip_key)
        cache.delete(self._user_key)
        cache.delete(self._lockout_key)

    def get_remaining_lockout(self) -> int:
        lockout_ts = cache.get(self._lockout_key)
        if lockout_ts:
            elapsed = int(time.time() - lockout_ts)
            remaining = self.LOCKOUT_SECONDS - elapsed
            return max(0, remaining)
        return 0
