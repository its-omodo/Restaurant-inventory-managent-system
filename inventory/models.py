from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Product(models.Model):
    class Unit(models.TextChoices):
        KG = "KG", "Kilogram"
        LITRE = "L", "Litre"
        PIECE = "PCS", "Piece"
        BOX = "BOX", "Box"
        PACK = "PACK", "Pack"

    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    section = models.ForeignKey("branches.Section", on_delete=models.PROTECT, related_name="products")
    unit = models.CharField(max_length=10, choices=Unit.choices)
    minimum_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maximum_stock = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

    def __str__(self): return f"{self.sku} - {self.name}"

class StockTransaction(models.Model):
    class Type(models.TextChoices):
        IN = "IN", "Stock In"
        OUT = "OUT", "Stock Out"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        WASTE = "WASTE", "Waste"
        TRANSFER = "TRANSFER", "Transfer"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="transactions")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT)
    section = models.ForeignKey("branches.Section", on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.section.branch_id != self.branch_id:
            raise ValidationError("Section must belong to the selected branch.")
        if self.product.section_id != self.section_id:
            raise ValidationError("Product must belong to the selected section.")
        if self.transaction_type != self.Type.ADJUSTMENT and self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        if self.transaction_type == self.Type.ADJUSTMENT and self.quantity == 0:
            raise ValidationError("Adjustment cannot be zero.")
