"""Settings de desarrollo local.

Diferencias con produccion:
  - DEBUG activado por defecto.
  - API navegable de DRF disponible.
  - Cookies sin flag Secure (se sirve por http://localhost).
"""

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = ["*"] if DEBUG else ALLOWED_HOSTS  # noqa: F405

# API navegable util en desarrollo; en produccion solo JSON.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.JSONRenderer",
    ],
}

# En desarrollo, Vite sirve el frontend en otro puerto y hace proxy a la API.
# Si se accede directamente, CORS ya esta configurado en base.py.
