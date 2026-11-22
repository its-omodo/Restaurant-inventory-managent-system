from django.contrib import admin
from .models import SaleTransaction, SalesBudget


@admin.register(SaleTransaction)
class SaleTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_ref", "branch", "section", "amount", "transaction_time")
    list_filter = ("branch", "section")
    search_fields = ("transaction_ref",)


@admin.register(SalesBudget)
class SalesBudgetAdmin(admin.ModelAdmin):
    list_display = ("branch", "month", "amount")
    list_filter = ("branch",)
