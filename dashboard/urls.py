from django.urls import path
from .views import *

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("sales/record/", record_sale, name="record_sale"),
    path("sales/budget/", set_sales_budget, name="set_sales_budget"),
    path("inventory/", inventory, name="inventory"),
    path("inventory/receive/", receive, name="receive_stock"),
    path("inventory/issue/", issue, name="issue_stock"),
    path("inventory/adjust/", adjust, name="adjust_stock"),
    path("inventory/transfer/", transfer, name="transfer_stock"),
    path("staff/", staff, name="staff"),
    path("staff/create/", create_employee, name="create_employee"),
    path("purchasing/", purchasing, name="purchasing"),
    path("purchasing/create/", create_purchase_request, name="create_purchase_request"),
    path("purchasing/<int:request_id>/review/", approve_purchase, name="approve_purchase"),
    path("reports/", reports, name="reports"),
    path("audit/", audit_logs, name="audit_logs"),
    path("section/<int:section_id>/", section_detail, name="section_detail"),
]
