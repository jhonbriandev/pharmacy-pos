"""Modelo de usuario: el DNI es el nombre de usuario.

Se define un usuario personalizado desde el primer dia porque cambiarlo despues
obliga a migraciones destructivas y este sistema depende del rol en cada
decision de permisos (ver docs/decisiones.md, D4).
"""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

DNI_LENGTH = 8

validate_dni = RegexValidator(
    r"^\d{8}$",
    "El DNI debe tener exactamente 8 digitos numericos.",
)


class Role(models.TextChoices):
    """Roles funcionales del sistema.

    Los nombres tecnicos (izquierda) son estables: se guardan en la base de
    datos y se usan en los permisos. Los nombres visibles pueden cambiar sin
    migrar datos.
    """

    ADMIN = "ADMIN", "Administrador / Gerencia"
    REGENTE = "REGENTE", "Quimico farmaceutico"
    CAJERO = "CAJERO", "Cajero / Vendedor"
    ALMACEN = "ALMACEN", "Auxiliar de almacen"
    AUDITOR = "AUDITOR", "Auditor"


class User(AbstractUser):
    """Usuario del sistema, identificado por su DNI."""

    username = models.CharField(
        "DNI",
        max_length=DNI_LENGTH,
        unique=True,
        validators=[validate_dni],
        help_text="Documento Nacional de Identidad (8 digitos). Se usa para iniciar sesion.",
        error_messages={"unique": "Ya existe un usuario con ese DNI."},
    )
    role = models.CharField(
        "rol",
        max_length=20,
        choices=Role.choices,
        default=Role.CAJERO,
        db_index=True,
    )
    email = models.EmailField("correo electronico", blank=True)
    must_change_password = models.BooleanField(
        "debe cambiar contrasena",
        default=False,
        help_text="Se activa cuando un administrador restablece la contrasena.",
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["last_name", "first_name", "username"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        self.username = (self.username or "").strip()
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        """Nombre completo; si no se cargo, se usa el DNI."""
        return self.get_full_name().strip() or self.username

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN
