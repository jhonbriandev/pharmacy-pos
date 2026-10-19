"""Crea la cuenta administradora de arranque.

En produccion no hay registro publico: la primera cuenta se crea desde la
consola del servidor. El comando es idempotente, asi que tambien sirve para
recuperar el acceso si la unica cuenta de administracion queda bloqueada.

Uso:

    python manage.py create_admin --dni 12345678 --first-name Ana --last-name Torres

Si se omite ``--password``, se pide de forma interactiva y no queda en el
historial del shell ni en los logs del servidor.
"""

import getpass

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Role, User


class Command(BaseCommand):
    help = "Crea o reactiva una cuenta administradora (ADMIN)."

    def add_arguments(self, parser):
        parser.add_argument("--dni", required=True, help="DNI de 8 digitos.")
        parser.add_argument("--first-name", default="Administrador")
        parser.add_argument("--last-name", default="")
        parser.add_argument(
            "--password",
            help="Si se omite, se solicita de forma interactiva (recomendado).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dni = options["dni"].strip()
        if len(dni) != 8 or not dni.isdigit():
            raise CommandError("El DNI debe tener exactamente 8 digitos.")

        user = User.objects.filter(username=dni).first() or User(username=dni)
        created = user._state.adding
        user.first_name = options["first_name"].strip()
        user.last_name = options["last_name"].strip()
        user.role = Role.ADMIN
        user.is_active = True
        # Acceso al admin de Django solo para la cuenta de arranque. Los
        # usuarios creados desde la API no son staff.
        user.is_staff = True
        user.is_superuser = True

        password = options.get("password")
        if not password:
            password = getpass.getpass("Contrasena: ")
            confirmation = getpass.getpass("Repite la contrasena: ")
            if password != confirmation:
                raise CommandError("Las contrasenas no coinciden.")

        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error

        user.set_password(password)
        user.must_change_password = False
        user.save()

        action = "creada" if created else "actualizada"
        self.stdout.write(
            self.style.SUCCESS(f"Cuenta administradora {action}: DNI {user.username}")
        )

        if not settings.DEBUG:
            self.stdout.write(
                "  Recuerda: esta cuenta es la unica con acceso a /admin/. "
                "Las demas se gestionan desde la aplicacion."
            )
