from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "entity", "object_id")
    list_filter = ("action", "entity")
    search_fields = ("action", "entity", "object_id", "details", "user__username")
    readonly_fields = ("created_at", "user", "action", "entity", "object_id", "details", "ip_address")
