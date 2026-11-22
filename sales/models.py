from django.conf import settings
from django.db import models


class SaleTransaction(models.Model):
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="sales")
    section = models.ForeignKey("branches.Section", on_delete=models.PROTECT, related_name="sales")
    transaction_ref = models.CharField(max_length=80, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_time = models.DateTimeField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ["-transaction_time"]
        indexes = [
            models.Index(fields=["branch", "transaction_time"]),
            models.Index(fields=["section", "transaction_time"]),
        ]

    def __str__(self):
        return f"{self.transaction_ref} - {self.amount}"


class SalesBudget(models.Model):
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="sales_budgets")
    month = models.DateField(help_text="Use the first day of the budget month.")
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "month"], name="unique_branch_sales_budget_month")]
        ordering = ["-month", "branch"]

    def __str__(self):
        return f"{self.branch} - {self.month:%B %Y} - {self.amount}"
