from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Product, StockTransaction


def stock_balance(product):
    qs = StockTransaction.objects.filter(product=product)
    total = Decimal("0")
    for tx in qs.only("transaction_type", "quantity"):
        if tx.transaction_type in (StockTransaction.Type.IN, StockTransaction.Type.TRANSFER):
            total += tx.quantity
        elif tx.transaction_type in (StockTransaction.Type.OUT, StockTransaction.Type.WASTE):
            total -= tx.quantity
        elif tx.transaction_type == StockTransaction.Type.ADJUSTMENT:
            total += tx.quantity
    return total


def section_product_balance(product, section=None):
    return stock_balance(product)

@transaction.atomic
def receive_stock(*, product, quantity, user, reason, request):
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    tx = StockTransaction(product=product, branch=product.section.branch, section=product.section,
                          transaction_type=StockTransaction.Type.IN, quantity=quantity,
                          reason=reason, created_by=user)
    tx.full_clean(); tx.save()
    from audit.services import log_action
    log_action(request, "RECEIVE_STOCK", "StockTransaction", tx.pk,
               f"Received {quantity} {product.unit} of {product.sku}. Reason: {reason}")
    return tx

@transaction.atomic
def issue_stock(*, product, quantity, user, reason, request):
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    balance = stock_balance(product)
    if quantity > balance:
        raise ValidationError(f"Insufficient stock. Available: {balance} {product.unit}.")
    tx = StockTransaction(product=product, branch=product.section.branch, section=product.section,
                          transaction_type=StockTransaction.Type.OUT, quantity=quantity,
                          reason=reason, created_by=user)
    tx.full_clean(); tx.save()
    from audit.services import log_action
    log_action(request, "ISSUE_STOCK", "StockTransaction", tx.pk,
               f"Issued {quantity} {product.unit} of {product.sku}. Reason: {reason}")
    return tx

@transaction.atomic
def adjust_stock(*, product, delta, user, reason, request):
    if delta == 0:
        raise ValidationError("Adjustment cannot be zero.")
    balance = stock_balance(product)
    if balance + delta < 0:
        raise ValidationError(f"Adjustment would make stock negative. Available: {balance} {product.unit}.")
    tx = StockTransaction(product=product, branch=product.section.branch, section=product.section,
                          transaction_type=StockTransaction.Type.ADJUSTMENT, quantity=delta,
                          reason=reason, created_by=user)
    tx.full_clean(); tx.save()
    from audit.services import log_action
    log_action(request, "ADJUST_STOCK", "StockTransaction", tx.pk,
               f"Adjusted {product.sku} by {delta} {product.unit}. Reason: {reason}")
    return tx

@transaction.atomic
def transfer_stock(*, product, destination_section, quantity, user, reason, request):
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    if destination_section.branch_id == product.section.branch_id and destination_section.pk == product.section_id:
        raise ValidationError("Destination must be different from the source section.")
    if quantity > stock_balance(product):
        raise ValidationError(f"Insufficient stock. Available: {stock_balance(product)} {product.unit}.")
    # Transfers are represented by an OUT in the source section and an IN in the destination.
    source_tx = StockTransaction(product=product, branch=product.section.branch, section=product.section,
                                 transaction_type=StockTransaction.Type.OUT, quantity=quantity,
                                 reason=f"Transfer to {destination_section}: {reason}", created_by=user)
    source_tx.full_clean(); source_tx.save()
    destination_product = Product.objects.filter(sku=product.sku, section=destination_section, active=True).first()
    if not destination_product:
        raise ValidationError("The destination section does not have an active product with the same SKU.")
    dest_tx = StockTransaction(product=destination_product, branch=destination_section.branch,
                               section=destination_section, transaction_type=StockTransaction.Type.TRANSFER,
                               quantity=quantity, reason=f"Transfer from {product.section}: {reason}", created_by=user)
    dest_tx.full_clean(); dest_tx.save()
    from audit.services import log_action
    log_action(request, "TRANSFER_STOCK", "StockTransfer", dest_tx.pk,
               f"Transferred {quantity} {product.unit} of {product.sku} from {product.section} to {destination_section}. Reason: {reason}")
    return source_tx, dest_tx
