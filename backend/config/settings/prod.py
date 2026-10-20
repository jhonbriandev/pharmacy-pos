"""Settings de produccion (Render).

Requiere que estas variables de entorno existan en el panel de Render:
    DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS,
    DATABASE_URL, DJANGO_CSRF_TRUSTED_ORIGINS
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, env

DEBUG = False

# Si alguien arranca produccion con DEBUG activado, es mejor fallar de golpe.
if env.bool("DJANGO_DEBUG", default=False):
    raise ImproperlyConfigured("DJANGO_DEBUG no puede ser True en produccion.")

# HTTPS obligatorio: Render termina TLS y reenvia la peticion.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Los estaticos de Django (admin y panel navegable de la API) se sirven con
# manifiesto comprimido. El frontend NO se sirve desde aqui: vive en Vercel.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Panel navegable de DRF tambien en produccion, para operar y revisar la API
# desde el navegador. JSON va primero: los clientes (frontend, curl con
# Accept: */*) siguen recibiendo JSON; solo un navegador pide text/html.
# No relaja permisos: cada vista sigue exigiendo autenticacion y rol, y el
# login del panel reutiliza la sesion (usuario = DNI).
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
