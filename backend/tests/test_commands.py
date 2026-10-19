"""Pruebas de los comandos de gestion.

Lo que se verifica es lo que puede salir mal en produccion: crear la cuenta de
arranque, no duplicarla al reintentar y no aceptar contrasenas debiles.
"""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import Role, User

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "Farm@cia2026Segura"


def test_create_admin_creates_an_active_admin(db):
    call_command(
        "create_admin",
        dni="20000001",
        first_name="Ana",
        last_name="Torres",
        password=STRONG_PASSWORD,
        verbosity=0,
    )

    user = User.objects.get(username="20000001")
    assert user.role == Role.ADMIN
    assert user.is_active is True
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password(STRONG_PASSWORD)
    assert user.must_change_password is False


def test_create_admin_is_idempotent_and_resets_the_password(db):
    call_command("create_admin", dni="20000002", password=STRONG_PASSWORD, verbosity=0)
    call_command("create_admin", dni="20000002", password="OtraClave2026", verbosity=0)

    assert User.objects.filter(username="20000002").count() == 1
    user = User.objects.get(username="20000002")
    assert user.check_password("OtraClave2026")


def test_create_admin_reactivates_a_disabled_account(db):
    user = User.objects.create_user(username="20000003", password=STRONG_PASSWORD)
    user.is_active = False
    user.save(update_fields=["is_active"])

    call_command("create_admin", dni="20000003", password=STRONG_PASSWORD, verbosity=0)

    user.refresh_from_db()
    assert user.is_active is True
    assert user.role == Role.ADMIN


def test_create_admin_rejects_a_bad_dni(db):
    with pytest.raises(CommandError, match="8 digitos"):
        call_command("create_admin", dni="123", password=STRONG_PASSWORD, verbosity=0)


def test_create_admin_rejects_a_weak_password(db):
    with pytest.raises(CommandError):
        call_command("create_admin", dni="20000004", password="12345678", verbosity=0)

    assert not User.objects.filter(username="20000004").exists()


def test_seed_is_blocked_when_debug_is_off(db, settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="solo debe ejecutarse en desarrollo"):
        call_command("seed", verbosity=0)
