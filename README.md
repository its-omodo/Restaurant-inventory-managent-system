# Restaurant Management System

Django-based multi-branch restaurant management system with Chicken and Pizza sections.

## Dashboard
- Current sales: today's sales total and current-day transaction list.
- Month-to-date sales: first day of the month through yesterday, excluding today's sales.
- Monthly sales budget and cumulative actual-vs-budget line graph.
- Stock gauges: Critical, Healthy, and Above Stockhold.
- Staff currently present with section and assigned station.
- Successful application logins redirect to the dashboard.

## Operational workflows
- Receive Stock
- Issue Stock
- Adjust Stock
- Stock Transfer
- Record Sale
- Set Sales Budget
- Create Employee
- Create Purchase Request
- Approve / Reject Purchase Request
- Audit Log

## Setup

```bash
cd restaurant_management_ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Open `http://YOUR_VM_IP:8000/`.

Application login: `/login/`
Django administration: `/admin/`

## Deploy to Render

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select this repository.
3. Render will read `render.yaml`, create the web service and PostgreSQL database, and run migrations during deployment.

The deployment uses environment variables for `SECRET_KEY` and the database connection. Do not commit the local SQLite database or secrets.

For other production hosts, configure PostgreSQL through `DATABASE_URL` or `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`; set a secure `SECRET_KEY`, set `DEBUG=False`, and configure `ALLOWED_HOSTS`.
