from django.contrib import admin
from .models import Supplier, PurchaseRequest, PurchaseRequestItem
admin.site.register(Supplier)
admin.site.register(PurchaseRequest)
admin.site.register(PurchaseRequestItem)
