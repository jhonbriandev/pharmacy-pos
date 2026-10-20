"""Configuracion comun a todos los entornos.

Todos los valores sensibles o dependientes del entorno se leen de variables de
entorno (archivo backend/.env en desarrollo). Este archivo no contiene secretos.
"""

from pathlib import Path

import environ
from corsheaders.defaults import default_headers

# backend/  (este archivo vive en backend/config/settings/base.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CONN_MAX_AGE=(int, 60),
    DJANGO_TIME_ZONE=(str, "America/Lima"),
    DJANGO_LANGUAGE_CODE=(str, "es-pe"),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    DJANGO_CORS_ALLOWED_ORIGINS=(list, []),
    DJANGO_LOG_LEVEL=(str, "INFO"),
    DJANGO_USE_X_FORWARDED_PROTO=(bool, False),
)

ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    env.read_env(str(ENV_FILE))

# ---------------------------------------------------------------------------
# Seguridad basica
# ---------------------------------------------------------------------------
# Obligatoria: si falta, el arranque falla con un mensaje claro en lugar de
# arrancar con una clave insegura por defecto.
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.catalog",
    "apps.inventory",
    "apps.sales",
    "apps.reporting",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # CorsMiddleware debe ir antes de CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de datos (PostgreSQL unicamente; nunca SQLite)
# ---------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env("DJANGO_CONN_MAX_AGE")
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 10)
DATABASES["default"]["ATOMIC_REQUESTS"] = False

# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Sesion en cookie HttpOnly (ver docs/decisiones.md, D2).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 horas: un turno
SESSION_SAVE_EVERY_REQUEST = True  # expiracion deslizante
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # equipos compartidos en mostrador

# El frontend lee esta cookie para enviar el header X-CSRFToken.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

# Cookies "Secure" se activan en produccion (config/settings/prod.py).

# Destino tras entrar o salir por el panel navegable de DRF (/api-auth/).
LOGIN_REDIRECT_URL = "/api/v1/"
LOGOUT_REDIRECT_URL = "/api/v1/"

# ---------------------------------------------------------------------------
# CORS (solo desarrollo y despliegues separados; en produccion se recomienda
# el proxy de Vercel para que el navegador vea un unico origen)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "sales": "240/min",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# ---------------------------------------------------------------------------
# Internacionalizacion y zona horaria
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE")
TIME_ZONE = env("DJANGO_TIME_ZONE")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estaticos
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Varios
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging: nunca se registran cuerpos de login ni secretos.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL"),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "mypos": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL"),
            "propagate": False,
        },
    },
}
