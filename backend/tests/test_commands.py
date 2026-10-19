"""Pruebas de los comandos de gestion.

Lo que se verifica es lo que puede salir mal en produccion: crear la cuenta de
arranque, no duplicarla al reintentar y no aceptar contrasenas debiles.
"""

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import Role, User

STRONG_PASSWORD = "Farm@cia2026Segura"


class ManagementCommandTests(TestCase):
    def test_create_admin_creates_an_active_admin(self):
        call_command(
            "create_admin",
            dni="20000001",
            first_name="Ana",
            last_name="Torres",
            password=STRONG_PASSWORD,
            verbosity=0,
        )

        user = User.objects.get(username="20000001")
        self.assertEqual(user.role, Role.ADMIN)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertFalse(user.must_change_password)

    def test_create_admin_is_idempotent_and_resets_the_password(self):
        call_command("create_admin", dni="20000002", password=STRONG_PASSWORD, verbosity=0)
        call_command("create_admin", dni="20000002", password="OtraClave2026", verbosity=0)

        self.assertEqual(User.objects.filter(username="20000002").count(), 1)
        user = User.objects.get(username="20000002")
        self.assertTrue(user.check_password("OtraClave2026"))

    def test_create_admin_reactivates_a_disabled_account(self):
        user = User.objects.create_user(username="20000003", password=STRONG_PASSWORD)
        user.is_active = False
        user.save(update_fields=["is_active"])

        call_command("create_admin", dni="20000003", password=STRONG_PASSWORD, verbosity=0)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.role, Role.ADMIN)

    def test_create_admin_rejects_a_bad_dni(self):
        with self.assertRaisesRegex(CommandError, "8 digitos"):
            call_command("create_admin", dni="123", password=STRONG_PASSWORD, verbosity=0)

    def test_create_admin_rejects_a_weak_password(self):
        with self.assertRaises(CommandError):
            call_command("create_admin", dni="20000004", password="12345678", verbosity=0)

        self.assertFalse(User.objects.filter(username="20000004").exists())

    def test_seed_is_blocked_when_debug_is_off(self):
        with (
            self.settings(DEBUG=False),
            self.assertRaisesRegex(CommandError, "solo debe ejecutarse en desarrollo"),
        ):
            call_command("seed", verbosity=0)
