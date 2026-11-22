from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal
import calendar
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import Role
from branches.models import Branch, Section
from inventory.models import Product, StockTransaction
from inventory.services import adjust_stock, issue_stock, receive_stock, stock_balance, transfer_stock
from staff.models import Employee
from purchasing.models import Supplier, PurchaseRequest, PurchaseRequestItem
from audit.models import AuditLog
from audit.services import log_action
from sales.models import SaleTransaction, SalesBudget
from .forms import StockMovementForm, AdjustmentForm, TransferForm, EmployeeForm, PurchaseRequestForm, ApprovalForm, SaleTransactionForm, SalesBudgetForm

def scoped_sections(user):
    if user.has_global_access():
        return Section.objects.select_related("branch").all()
    if user.role == Role.RGM:
        return Section.objects.filter(branch__in=user.branches.all()).select_related("branch")
    return user.sections.all().select_related("branch")

def can_manage_staff(user):
    return user.has_global_access() or user.role == Role.RGM

def can_approve_purchase(user):
    return user.has_global_access() or user.role == Role.RGM

def render_form(request, form, title, description=""):
    return render(request, "forms/form.html", {"page_title": title, "form": form, "description": description})

@login_required
def dashboard(request):
    sections = scoped_sections(request.user)
    branches = Branch.objects.filter(sections__in=sections).distinct()
    products = Product.objects.filter(section__in=sections, active=True).select_related("section", "section__branch")

    # Dashboard sales periods use Nairobi/local application time. MTD deliberately excludes today.
    now = timezone.localtime()
    today = now.date()
    month_start = today.replace(day=1)
    yesterday_start = timezone.make_aware(datetime.combine(today - timedelta(days=1), time.min))
    today_start = timezone.make_aware(datetime.combine(today, time.min))
    tomorrow_start = today_start + timedelta(days=1)

    accessible_sales = SaleTransaction.objects.filter(section__in=sections)
    today_sales_qs = accessible_sales.filter(transaction_time__gte=today_start, transaction_time__lt=tomorrow_start)
    current_transaction_count = today_sales_qs.count()
    current_transactions = today_sales_qs.select_related("branch", "section")[:12]
    current_sales = today_sales_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    mtd_sales = accessible_sales.filter(transaction_time__gte=timezone.make_aware(datetime.combine(month_start, time.min)), transaction_time__lt=today_start).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Stock health: critical <= minimum; healthy > minimum and <= maximum; above stockhold > maximum.
    stock_counts = {"critical": 0, "healthy": 0, "above": 0}
    for product in products:
        balance = stock_balance(product)
        if balance <= product.minimum_stock:
            stock_counts["critical"] += 1
        elif product.maximum_stock is not None and balance > product.maximum_stock:
            stock_counts["above"] += 1
        else:
            stock_counts["healthy"] += 1
    stock_total = sum(stock_counts.values()) or 1
    stock_gauges = {
        "critical": {"count": stock_counts["critical"], "pct": round(stock_counts["critical"] * 100 / stock_total, 1)},
        "healthy": {"count": stock_counts["healthy"], "pct": round(stock_counts["healthy"] * 100 / stock_total, 1)},
        "above": {"count": stock_counts["above"], "pct": round(stock_counts["above"] * 100 / stock_total, 1)},
    }

    # Budget and actuals are cumulative through yesterday so the graph compares like-for-like periods.
    budget_total = SalesBudget.objects.filter(branch__in=branches, month=month_start).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    daily_actuals = {}
    sales_month_qs = accessible_sales.filter(transaction_time__gte=timezone.make_aware(datetime.combine(month_start, time.min)), transaction_time__lt=today_start)
    for row in sales_month_qs.values("transaction_time__date").annotate(total=Sum("amount")):
        daily_actuals[row["transaction_time__date"]] = row["total"] or Decimal("0")

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    graph_points = []
    cumulative_actual = Decimal("0")
    max_value = max(float(budget_total), float(mtd_sales), 1.0)
    # Use a straight-line budget pace unless branch-specific daily budget allocation is later introduced.
    for day in range(1, today.day):
        d = month_start + timedelta(days=day - 1)
        cumulative_actual += daily_actuals.get(d, Decimal("0"))
        budget_cumulative = (budget_total * Decimal(day) / Decimal(days_in_month)) if budget_total else Decimal("0")
        max_value = max(max_value, float(cumulative_actual), float(budget_cumulative))
        graph_points.append({"label": d.strftime("%d %b"), "actual": cumulative_actual, "budget": budget_cumulative})
    graph_w, graph_h, graph_left, graph_right, graph_top, graph_bottom = 900, 300, 55, 880, 25, 255
    usable_w, usable_h = graph_right - graph_left, graph_bottom - graph_top
    for i, point in enumerate(graph_points):
        x = graph_left if len(graph_points) == 1 else graph_left + usable_w * i / (len(graph_points) - 1)
        actual_y = graph_bottom - usable_h * float(point["actual"]) / max_value
        budget_y = graph_bottom - usable_h * float(point["budget"]) / max_value
        point["x"], point["actual_y"], point["budget_y"] = round(x, 1), round(actual_y, 1), round(budget_y, 1)
    actual_polyline = " ".join(f'{p["x"]},{p["actual_y"]}' for p in graph_points)
    budget_polyline = " ".join(f'{p["x"]},{p["budget_y"]}' for p in graph_points)

    # Staff currently present: clocked in today with no clock-out, plus today's shift/station.
    from staff.models import Attendance, Shift
    present = []
    attendance_qs = Attendance.objects.filter(employee__section__in=sections, date=today, clock_in__isnull=False, clock_out__isnull=True).select_related("employee", "employee__branch", "employee__section")
    shifts = Shift.objects.filter(employee__in=[a.employee_id for a in attendance_qs], date=today).select_related("section")
    shift_map = {s.employee_id: s for s in shifts}
    for attendance in attendance_qs:
        shift = shift_map.get(attendance.employee_id)
        present.append({"employee": attendance.employee, "clock_in": attendance.clock_in, "shift": shift, "station": shift.station if shift and shift.station else "Not assigned"})

    context = {
        "branches": branches, "sections": sections, "products_count": products.count(),
        "employees_count": Employee.objects.filter(section__in=sections, active=True).count(),
        "transactions_count": StockTransaction.objects.filter(section__in=sections).count(),
        "suppliers_count": Supplier.objects.filter(active=True).count(),
        "purchase_requests_count": PurchaseRequest.objects.filter(section__in=sections).count(),
        "low_stock_count": stock_counts["critical"], "current_sales": current_sales,
        "current_transactions": current_transactions, "current_transaction_count": current_transaction_count, "mtd_sales": mtd_sales,
        "budget_total": budget_total, "stock_gauges": stock_gauges, "stock_total": sum(stock_counts.values()),
        "present_staff": present, "graph_points": graph_points, "actual_polyline": actual_polyline,
        "budget_polyline": budget_polyline, "graph_max": max_value, "month_label": today.strftime("%B %Y"),
        "page_title": "Dashboard",
    }
    return render(request, "dashboard/index.html", context)

@login_required
def record_sale(request):
    sections = scoped_sections(request.user)
    form = SaleTransactionForm(request.POST or None, sections=sections)
    if request.method == "POST" and form.is_valid():
        sale = SaleTransaction.objects.create(
            branch=form.cleaned_data["branch"], section=form.cleaned_data["section"],
            transaction_ref=form.cleaned_data["transaction_ref"], amount=form.cleaned_data["amount"],
            transaction_time=form.cleaned_data["transaction_time"], recorded_by=request.user,
        )
        log_action(request, "RECORD_SALE", "SaleTransaction", sale.pk, f"Recorded sale {sale.transaction_ref} for {sale.amount}.")
        messages.success(request, "Sale transaction recorded successfully.")
        return redirect("dashboard")
    return render_form(request, form, "Record Sale", "Record a sales transaction so it appears on the current-sales dashboard.")

@login_required
def set_sales_budget(request):
    branches = Branch.objects.filter(sections__in=scoped_sections(request.user)).distinct()
    if not (request.user.has_global_access() or request.user.role == Role.RGM):
        messages.error(request, "You do not have permission to set sales budgets.")
        return redirect("dashboard")
    form = SalesBudgetForm(request.POST or None, branches=branches)
    if request.method == "POST" and form.is_valid():
        budget, _ = SalesBudget.objects.update_or_create(
            branch=form.cleaned_data["branch"], month=form.cleaned_data["month"],
            defaults={"amount": form.cleaned_data["amount"]},
        )
        log_action(request, "SET_SALES_BUDGET", "SalesBudget", budget.pk, f"Set {budget.branch} budget for {budget.month:%B %Y} to {budget.amount}.")
        messages.success(request, "Sales budget saved successfully.")
        return redirect("dashboard")
    return render_form(request, form, "Set Sales Budget", "Set the monthly sales budget used by the dashboard line graph.")

@login_required
def inventory(request):
    sections = scoped_sections(request.user)
    products = Product.objects.filter(section__in=sections, active=True).select_related("section", "category")
    rows = [(p, stock_balance(p)) for p in products]
    return render(request, "dashboard/inventory.html", {"page_title":"Inventory", "products":products, "rows":rows, "sections":sections})

@login_required
def receive(request):
    sections = scoped_sections(request.user)
    form = StockMovementForm(request.POST or None, sections=sections, movement="in")
    if request.method == "POST" and form.is_valid():
        try:
            receive_stock(product=form.cleaned_data["product"], quantity=form.cleaned_data["quantity"], user=request.user, reason=form.cleaned_data["reason"], request=request)
            messages.success(request, "Stock received successfully.")
            return redirect("inventory")
        except ValidationError as e: form.add_error(None, e.messages)
    return render_form(request, form, "Receive Stock", "Record stock received into a Chicken or Pizza section.")

@login_required
def issue(request):
    sections = scoped_sections(request.user)
    form = StockMovementForm(request.POST or None, sections=sections, movement="out")
    if request.method == "POST" and form.is_valid():
        try:
            issue_stock(product=form.cleaned_data["product"], quantity=form.cleaned_data["quantity"], user=request.user, reason=form.cleaned_data["reason"], request=request)
            messages.success(request, "Stock issued successfully.")
            return redirect("inventory")
        except ValidationError as e: form.add_error(None, e.messages)
    return render_form(request, form, "Issue Stock", "Issue stock for production, sales, or other approved use.")

@login_required
def adjust(request):
    sections = scoped_sections(request.user)
    form = AdjustmentForm(request.POST or None, sections=sections)
    if request.method == "POST" and form.is_valid():
        try:
            adjust_stock(product=form.cleaned_data["product"], delta=form.cleaned_data["delta"], user=request.user, reason=form.cleaned_data["reason"], request=request)
            messages.success(request, "Stock adjusted successfully.")
            return redirect("inventory")
        except ValidationError as e: form.add_error(None, e.messages)
    return render_form(request, form, "Adjust Stock", "Use a positive number to increase stock or a negative number to decrease it.")

@login_required
def transfer(request):
    sections = scoped_sections(request.user)
    form = TransferForm(request.POST or None, sections=sections)
    if request.method == "POST" and form.is_valid():
        try:
            transfer_stock(product=form.cleaned_data["product"], destination_section=form.cleaned_data["destination_section"], quantity=form.cleaned_data["quantity"], user=request.user, reason=form.cleaned_data["reason"], request=request)
            messages.success(request, "Stock transferred successfully.")
            return redirect("inventory")
        except ValidationError as e: form.add_error(None, e.messages)
    return render_form(request, form, "Stock Transfer", "Transfer stock between accessible Chicken/Pizza sections that share the same SKU.")

@login_required
def staff(request):
    sections = scoped_sections(request.user)
    employees = Employee.objects.filter(section__in=sections, active=True).select_related("branch", "section")
    return render(request, "dashboard/staff.html", {"page_title":"Staff", "employees":employees, "sections":sections, "can_manage_staff":can_manage_staff(request.user)})

@login_required
def create_employee(request):
    sections = scoped_sections(request.user)
    if not can_manage_staff(request.user):
        messages.error(request, "You do not have permission to create employees.")
        return redirect("staff")
    form = EmployeeForm(request.POST or None, sections=sections)
    if request.method == "POST" and form.is_valid():
        employee = form.save()
        log_action(request, "CREATE", "Employee", employee.pk, f"Created {employee}")
        messages.success(request, "Employee created successfully.")
        return redirect("staff")
    return render_form(request, form, "Create Employee", "Add a staff member to an accessible branch and section.")

@login_required
def purchasing(request):
    sections = scoped_sections(request.user)
    requests = PurchaseRequest.objects.filter(section__in=sections).select_related("branch", "section", "requested_by").prefetch_related("items__product").order_by("-created_at")
    return render(request, "dashboard/purchasing.html", {"page_title":"Purchasing", "requests":requests, "can_approve":can_approve_purchase(request.user)})

@login_required
@transaction.atomic
def create_purchase_request(request):
    sections = scoped_sections(request.user)
    form = PurchaseRequestForm(request.POST or None, sections=sections)
    if request.method == "POST" and form.is_valid():
        pr = PurchaseRequest.objects.create(branch=form.cleaned_data["branch"], section=form.cleaned_data["section"], requested_by=request.user, status=PurchaseRequest.Status.SUBMITTED, notes=form.cleaned_data["notes"])
        PurchaseRequestItem.objects.create(request=pr, product=form.cleaned_data["product"], quantity=form.cleaned_data["quantity"])
        log_action(request, "CREATE_PURCHASE_REQUEST", "PurchaseRequest", pr.pk, f"Submitted purchase request for {form.cleaned_data['quantity']} {form.cleaned_data['product'].unit} of {form.cleaned_data['product']}")
        messages.success(request, "Purchase request submitted.")
        return redirect("purchasing")
    return render_form(request, form, "Create Purchase Request", "Submit a purchase request for an accessible section.")

@login_required
@transaction.atomic
def approve_purchase(request, request_id):
    sections = scoped_sections(request.user)
    purchase = get_object_or_404(PurchaseRequest.objects.select_related("section"), pk=request_id, section__in=sections)
    if not can_approve_purchase(request.user):
        messages.error(request, "You do not have permission to approve purchase requests.")
        return redirect("purchasing")
    if purchase.status != PurchaseRequest.Status.SUBMITTED:
        messages.warning(request, "Only submitted requests can be approved or rejected.")
        return redirect("purchasing")
    form = ApprovalForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        decision = form.cleaned_data["decision"]
        purchase.status = decision
        purchase.save(update_fields=["status"])
        log_action(request, f"PURCHASE_{decision}", "PurchaseRequest", purchase.pk, form.cleaned_data["notes"])
        messages.success(request, f"Purchase request {decision.lower()}.")
        return redirect("purchasing")
    return render_form(request, form, f"Review Purchase Request #{purchase.pk}", f"Requested by {purchase.requested_by}. Current status: {purchase.get_status_display()}.")

@login_required
def reports(request):
    sections = scoped_sections(request.user)
    return render(request, "dashboard/reports.html", {"page_title":"Reports", "sections":sections,
        "products_count":Product.objects.filter(section__in=sections, active=True).count(),
        "employees_count":Employee.objects.filter(section__in=sections, active=True).count(),
        "transactions_count":StockTransaction.objects.filter(section__in=sections).count(),
        "audit_count":AuditLog.objects.filter(entity__in=["StockTransaction","StockTransfer","Employee","PurchaseRequest"]).count()})

@login_required
def audit_logs(request):
    if not request.user.has_global_access():
        messages.error(request, "Only full-access roles can view the audit log.")
        return redirect("dashboard")
    logs = AuditLog.objects.select_related("user")[:250]
    return render(request, "dashboard/audit.html", {"page_title":"Audit Log", "logs":logs})

@login_required
def section_detail(request, section_id):
    section = get_object_or_404(scoped_sections(request.user), pk=section_id)
    products = Product.objects.filter(section=section, active=True).select_related("category")
    employees = Employee.objects.filter(section=section, active=True)
    transactions = StockTransaction.objects.filter(section=section).select_related("product", "created_by").order_by("-created_at")[:20]
    return render(request, "dashboard/section.html", {"page_title":section.get_name_display(), "section":section, "products":products, "employees":employees, "transactions":transactions, "balances": {p.pk:stock_balance(p) for p in products}})
