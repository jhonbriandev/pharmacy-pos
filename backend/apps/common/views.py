"""Vistas transversales (no pertenecen a ningun dominio)."""

from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@require_GET
def healthz(request):
    """Sonda de vida para el keep-warm y el health check de Render.

    A proposito NO consulta la base de datos: hacerlo despertaria Neon en cada
    ping y agotaria las horas de computo gratuitas. Para comprobar la base de
    datos existe la sonda de preparacion, que se usa con menos frecuencia.
    """
    return JsonResponse({"status": "ok", "service": "my-pos-api"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_root(request):
    """Indice de la API: punto de entrada del panel navegable de DRF.

    Solo resuelve nombres de ruta (``reverse``); no consulta ni importa otras
    apps, asi que respeta la regla de dependencias de ``common``.
    """
    return Response(
        {
            "autenticacion": {
                "csrf": reverse("accounts:csrf"),
                "login": reverse("accounts:login"),
                "logout": reverse("accounts:logout"),
                "me": reverse("accounts:me"),
            },
            "usuarios": {
                "lista": reverse("accounts:user-list"),
                "roles": reverse("accounts:role-list"),
            },
            "catalogo": {
                "productos": reverse("product-list"),
                "grupos": reverse("product-group-list"),
                "laboratorios": reverse("laboratory-list"),
                "categorias": reverse("category-list"),
                "principios_activos": reverse("active-ingredient-list"),
                "conversiones": reverse("unit-conversion-list"),
            },
            "inventario": {
                "lotes": reverse("lot-list"),
                "entradas": reverse("stock-entry-list"),
                "movimientos": reverse("stock-movement-list"),
                "consistencia": reverse("inventory-consistency"),
            },
            "ventas": {
                "lista": reverse("sale-list"),
            },
            "reportes": {
                "dashboard": reverse("reporting:dashboard"),
            },
            "auditoria": {
                "eventos": reverse("audit-event-list"),
                "meta": reverse("meta"),
            },
        }
    )
