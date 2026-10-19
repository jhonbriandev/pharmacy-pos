"""Vistas transversales (no pertenecen a ningun dominio)."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    """Sonda de vida para el keep-warm y el health check de Render.

    A proposito NO consulta la base de datos: hacerlo despertaria Neon en cada
    ping y agotaria las horas de computo gratuitas. Para comprobar la base de
    datos existe la sonda de preparacion, que se usa con menos frecuencia.
    """
    return JsonResponse({"status": "ok", "service": "my-pos-api"})
