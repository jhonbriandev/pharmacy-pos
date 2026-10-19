"""Constructores de objetos ficticios para las pruebas."""

from apps.accounts.models import User

PASSWORD = "PruebaSegura123"


def make_user(username: str, role: str, **kwargs) -> User:
    """Crea un usuario activo con contrasena conocida."""
    user = User(
        username=username,
        role=role,
        first_name="Prueba",
        last_name=role.title(),
        **kwargs,
    )
    user.set_password(PASSWORD)
    user.save()
    return user
