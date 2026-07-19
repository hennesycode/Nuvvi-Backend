import logging

from .models import AuditLog

logger = logging.getLogger("django")


def get_client_ip(request):
    if not request:
        return None
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def write_audit_log(*, request=None, actor=None, action, entity, entity_id=None, status=AuditLog.STATUS_SUCCESS, message="", error_message="", metadata=None):
    try:
        user = actor
        if user is None and request is not None and getattr(request, "user", None) and request.user.is_authenticated:
            user = request.user

        return AuditLog.objects.create(
            actor=user,
            action=action,
            entity=entity,
            entity_id=entity_id,
            status=status,
            message=message[:255] if message else "",
            error_message=str(error_message) if error_message else "",
            request_method=getattr(request, "method", "") if request else "",
            request_path=getattr(request, "path", "")[:255] if request else "",
            ip_address=get_client_ip(request),
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.warning("AUDIT: no se pudo registrar actividad: %s", exc)
        return None
