import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role, User


class Command(BaseCommand):
    help = "Create an initial administrator from bootstrap environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "").strip()
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
        if not username or not password:
            raise CommandError(
                "Set both BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD."
            )
        if len(password) < 14:
            raise CommandError("The bootstrap password must be at least 14 characters.")

        if User.objects.filter(username=username).exists():
            self.stdout.write("Bootstrap username already exists; no account was changed.")
            return

        user = User(
            username=username,
            role=Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError("The bootstrap password is not acceptable: " + "; ".join(exc.messages)) from exc

        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS("Administrator account created."))
