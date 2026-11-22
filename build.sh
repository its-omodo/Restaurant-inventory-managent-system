#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

if [ -n "${BOOTSTRAP_ADMIN_USERNAME:-}" ] || [ -n "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
    python manage.py bootstrap_admin
fi
