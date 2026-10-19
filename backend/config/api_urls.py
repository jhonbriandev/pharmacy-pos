"""Rutas de la API versionada.

Cada aplicacion expone sus propias rutas y aqui se componen. Mantener un unico
punto de composicion evita que las apps se conozcan entre si.
"""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.inventory.urls")),
    path("", include("apps.sales.urls")),
    path("", include("apps.reporting.urls")),
    path("", include("apps.audit.urls")),
]
