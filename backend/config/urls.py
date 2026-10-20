"""URLs raiz del proyecto."""

from django.contrib import admin
from django.urls import include, path

from apps.common.views import healthz

admin.site.site_header = "my-pos · Administracion"
admin.site.site_title = "my-pos"
admin.site.index_title = "Panel de administracion"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", healthz, name="healthz"),
    # Login/logout para el panel navegable de DRF. Publica los nombres
    # rest_framework:login/logout con las vistas propias de accounts (misma
    # sesion, mismo freno por IP y misma auditoria que el login de la API).
    path("api-auth/", include("apps.accounts.panel_urls")),
    path("api/v1/", include("config.api_urls")),
]
