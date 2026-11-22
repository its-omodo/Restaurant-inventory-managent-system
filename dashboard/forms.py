from django import forms
from django.core.exceptions import ValidationError
from branches.models import Branch, Section
from inventory.models import Product
from staff.models import Employee
from purchasing.models import PurchaseRequest, PurchaseRequestItem
from inventory.services import stock_balance

class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")

class StockMovementForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none(), label="Product")
    quantity = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=12)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True)

    def __init__(self, *args, sections=None, movement="in", **kwargs):
        super().__init__(*args, **kwargs)
        self.sections = sections
        self.movement = movement
        self.fields["product"].queryset = Product.objects.filter(section__in=sections, active=True).select_related("section")

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        qty = cleaned.get("quantity")
        if product and qty and self.movement in ("out", "transfer") and qty > stock_balance(product):
            raise ValidationError(f"Only {stock_balance(product)} {product.unit} is available for {product.name}.")
        return cleaned

class AdjustmentForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    delta = forms.DecimalField(max_digits=12, decimal_places=2, required=True, label="Adjustment (+/-)")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, sections=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(section__in=sections, active=True)

    def clean_delta(self):
        value = self.cleaned_data["delta"]
        if value == 0:
            raise ValidationError("Adjustment cannot be zero.")
        return value

class TransferForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    destination_section = forms.ModelChoiceField(queryset=Section.objects.none(), label="Destination section")
    quantity = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=12)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, sections=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sections = sections
        self.fields["product"].queryset = Product.objects.filter(section__in=sections, active=True).select_related("section")
        self.fields["destination_section"].queryset = sections

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        dest = cleaned.get("destination_section")
        qty = cleaned.get("quantity")
        if product and dest and product.section_id == dest.pk:
            raise ValidationError("Destination must be different from the source section.")
        if product and qty and qty > stock_balance(product):
            raise ValidationError(f"Only {stock_balance(product)} {product.unit} is available.")
        if product and dest and not Product.objects.filter(sku=product.sku, section=dest, active=True).exists():
            raise ValidationError("Destination section must have the same active SKU before a transfer.")
        return cleaned

class EmployeeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["employee_number", "first_name", "last_name", "phone", "email", "position", "branch", "section", "active"]

    def __init__(self, *args, sections=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sections = sections
        self.fields["branch"].queryset = Branch.objects.filter(sections__in=sections).distinct()
        self.fields["section"].queryset = sections

    def clean(self):
        cleaned = super().clean()
        branch, section = cleaned.get("branch"), cleaned.get("section")
        if branch and section and section.branch_id != branch.pk:
            raise ValidationError("Section must belong to the selected branch.")
        return cleaned

class PurchaseRequestForm(StyledFormMixin, forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.none())
    section = forms.ModelChoiceField(queryset=Section.objects.none())
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.DecimalField(min_value=0.01, decimal_places=2, max_digits=12)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, sections=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(sections__in=sections).distinct()
        self.fields["section"].queryset = sections
        self.fields["product"].queryset = Product.objects.filter(section__in=sections, active=True)

    def clean(self):
        cleaned = super().clean()
        branch, section, product = cleaned.get("branch"), cleaned.get("section"), cleaned.get("product")
        if branch and section and section.branch_id != branch.pk:
            raise ValidationError("Section must belong to the selected branch.")
        if section and product and product.section_id != section.pk:
            raise ValidationError("Product must belong to the selected section.")
        return cleaned

class ApprovalForm(StyledFormMixin, forms.Form):
    decision = forms.ChoiceField(choices=[("APPROVED", "Approve"), ("REJECTED", "Reject")])
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

class SaleTransactionForm(StyledFormMixin, forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.none())
    section = forms.ModelChoiceField(queryset=Section.objects.none())
    transaction_ref = forms.CharField(max_length=80)
    amount = forms.DecimalField(min_value=0.01, max_digits=14, decimal_places=2)
    transaction_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    def __init__(self, *args, sections=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.filter(sections__in=sections).distinct()
        self.fields["section"].queryset = sections

    def clean(self):
        cleaned = super().clean()
        branch, section = cleaned.get("branch"), cleaned.get("section")
        if branch and section and section.branch_id != branch.pk:
            raise ValidationError("Section must belong to the selected branch.")
        return cleaned

class SalesBudgetForm(StyledFormMixin, forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.none())
    month = forms.DateField(widget=forms.DateInput(attrs={"type": "month"}), input_formats=["%Y-%m"])
    amount = forms.DecimalField(min_value=0, max_digits=14, decimal_places=2)

    def __init__(self, *args, branches=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = branches

    def clean_month(self):
        value = self.cleaned_data["month"]
        return value.replace(day=1)
