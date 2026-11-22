from .models import AuditLog

def log_action(request, action, entity, object_id="", details=""):
    return AuditLog.objects.create(
        user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
        action=action,
        entity=entity,
        object_id=str(object_id),
        details=details,
        ip_address=request.META.get("REMOTE_ADDR") if getattr(request, "META", None) else None,
    )
