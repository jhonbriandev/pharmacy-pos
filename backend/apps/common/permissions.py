"""Permisos genericos reutilizables.

Las clases concretas por rol viven en ``apps.accounts.permissions`` para que
``common`` no dependa de ningun dominio.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class HasRole(BasePermission):
    """Permite el acceso solo a los roles listados en ``roles``.

    Se usa como clase base: cada permiso concreto declara sus roles.
    """

    roles: tuple[str, ...] = ()
    message = "No tienes permisos para realizar esta accion."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or not user.is_active:
            return False
        return user.role in self.roles


class IsReadOnly(BasePermission):
    """Permite unicamente metodos seguros (GET, HEAD, OPTIONS)."""

    message = "Esta operacion solo permite lectura."

    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS


class ReadOnlyOrRoles(HasRole):
    """Lectura para cualquier usuario autenticado; escritura solo para ``roles``.

    Es el patron de los catalogos: todos consultan, pocos editan.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated or not user.is_active:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in self.roles
