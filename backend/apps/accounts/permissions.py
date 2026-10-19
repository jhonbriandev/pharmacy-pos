"""Permisos concretos por rol.

Se declaran como clases para que cada vista exprese su regla de forma legible:

    permission_classes = [IsBackOffice]

y para que la matriz de pruebas de permisos pueda importarlas y verificarlas.
"""

from apps.accounts.models import Role
from apps.common.permissions import HasRole, ReadOnlyOrRoles


class IsAdmin(HasRole):
    roles = (Role.ADMIN,)


class IsAdminOrRegent(HasRole):
    roles = (Role.ADMIN, Role.REGENTE)


class IsBackOffice(HasRole):
    """Gestion de inventario: administracion, regencia y almacen."""

    roles = (Role.ADMIN, Role.REGENTE, Role.ALMACEN)


class CanSell(HasRole):
    """Puede registrar ventas en el punto de venta."""

    roles = (Role.ADMIN, Role.REGENTE, Role.CAJERO)


class CanViewAllSales(HasRole):
    """Puede consultar las ventas de todo el equipo (no solo las propias)."""

    roles = (Role.ADMIN, Role.REGENTE, Role.AUDITOR)


class SalesAccess(HasRole):
    """Acceso al modulo de ventas.

    Leer: quien vende y quien audita. Escribir: solo quien vende. Separar ambas
    cosas permite que auditoria revise las ventas sin poder registrarlas.
    """

    roles = (Role.ADMIN, Role.REGENTE, Role.CAJERO, Role.AUDITOR)
    write_roles = (Role.ADMIN, Role.REGENTE, Role.CAJERO)

    def has_permission(self, request, view) -> bool:
        from rest_framework.permissions import SAFE_METHODS

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return user.role in self.roles
        return user.role in self.write_roles


class CanViewDashboard(HasRole):
    roles = (Role.ADMIN, Role.REGENTE)


class CanReadAudit(HasRole):
    roles = (Role.ADMIN, Role.AUDITOR)


class CanViewInventory(HasRole):
    """Consulta de inventario: incluye auditoria en modo lectura."""

    roles = (Role.ADMIN, Role.REGENTE, Role.ALMACEN, Role.AUDITOR)


class CanAdjustStock(HasRole):
    """Los ajustes mueven stock sin respaldo documental: solo gerencia y regencia."""

    roles = (Role.ADMIN, Role.REGENTE)


class IsCatalogEditor(ReadOnlyOrRoles):
    """Todos leen el catalogo; solo back office lo edita."""

    roles = (Role.ADMIN, Role.REGENTE, Role.ALMACEN)
