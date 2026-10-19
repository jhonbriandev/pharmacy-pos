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
    path("api/v1/", include("config.api_urls")),
]
