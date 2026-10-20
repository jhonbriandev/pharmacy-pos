"""Rutas de la API versionada.

Cada aplicacion expone sus propias rutas y aqui se componen. Mantener un unico
punto de composicion evita que las apps se conozcan entre si.
"""

from django.urls import include, path

from apps.common.views import api_root

urlpatterns = [
    # Indice de la API: pantalla inicial del panel navegable de DRF.
    # No colisiona con los includes: solo casa con la ruta vacia.
    path("", api_root, name="api-root"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.inventory.urls")),
    path("", include("apps.sales.urls")),
    path("", include("apps.reporting.urls")),
    path("", include("apps.audit.urls")),
]
