import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from accounts.models import Role, User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BootstrapAdminCommandTests(TestCase):
    @patch.dict(
        os.environ,
        {
            "BOOTSTRAP_ADMIN_USERNAME": "initial-admin",
            "BOOTSTRAP_ADMIN_PASSWORD": "A-long-unique-password-8492!",
        },
    )
    def test_creates_global_admin(self):
        call_command("bootstrap_admin", stdout=StringIO())

        user = User.objects.get(username="initial-admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, Role.ADMIN)
        self.assertTrue(user.check_password("A-long-unique-password-8492!"))

    @patch.dict(
        os.environ,
        {
            "BOOTSTRAP_ADMIN_USERNAME": "existing-user",
            "BOOTSTRAP_ADMIN_PASSWORD": "A-new-unique-password-8492!",
        },
    )
    def test_does_not_change_existing_user(self):
        existing = User.objects.create_user(
            username="existing-user",
            password="An-old-unique-password-8492!",
        )

        call_command("bootstrap_admin", stdout=StringIO())

        existing.refresh_from_db()
        self.assertTrue(existing.check_password("An-old-unique-password-8492!"))
        self.assertFalse(existing.is_superuser)

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_both_environment_variables(self):
        with self.assertRaises(CommandError):
            call_command("bootstrap_admin", stdout=StringIO())
