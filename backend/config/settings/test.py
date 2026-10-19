"""Settings exclusivos de la suite de pruebas.

Se diferencia de ``dev`` solo en lo que hace que las pruebas sean rapidas y
deterministas, nunca en el comportamiento del dominio:

  - Hash de contrasena MD5: BCrypt/PBKDF2 tardan ~200 ms por usuario y la
    matriz de permisos crea cientos. El hash real se sigue usando en dev y prod.
  - Limites de throttling altos: el limite de login existe para frenar ataques
    de fuerza bruta, no para romper las pruebas que inician sesion muchas veces.
  - Correo en memoria: ninguna prueba debe intentar abrir una conexion SMTP.

La base de datos sigue siendo PostgreSQL. **Nunca SQLite**: las pruebas de
concurrencia con ``select_for_update`` no significan nada sin un motor real.
"""

from .dev import *  # noqa: F403
from .dev import REST_FRAMEWORK

DEBUG = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Sin throttling en pruebas: se prueba la logica, no el rate limit.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "login": "10000/min",
        "password_change": "10000/min",
        "anon": "10000/min",
        "user": "10000/min",
    },
    # Renderer JSON unicamente: el navegable genera HTML pesado e irrelevante.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# Las pruebas no deben escribir en el almacenamiento de estaticos.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
