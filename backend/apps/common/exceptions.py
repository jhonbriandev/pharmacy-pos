"""Errores uniformes de la API.

Todas las respuestas de error tienen la misma forma, para que el frontend no
tenga que adivinar:

    {
        "error": {
            "code": "insufficient_stock",
            "message": "No hay stock suficiente para el producto ...",
            "details": {...}
        }
    }
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler

MESSAGES: dict[str, str] = {
    "validation_error": "Los datos enviados no son validos.",
    "permission_denied": "No tienes permisos para realizar esta accion.",
    "not_authenticated": "Debes iniciar sesion para continuar.",
    "authentication_failed": "Usuario o contrasena incorrectos.",
    "not_found": "El recurso solicitado no existe.",
    "method_not_allowed": "Metodo no permitido.",
    "throttled": "Demasiados intentos. Espera un momento e intentalo de nuevo.",
    "parse_error": "El cuerpo de la peticion no es JSON valido.",
    "unsupported_media_type": "Tipo de contenido no soportado.",
    "error": "Ocurrio un error inesperado. Intenta de nuevo.",
}


class BusinessError(APIException):
    """Error de regla de negocio, con codigo estable para el frontend.

    Por defecto responde 409 (conflicto), que es lo correcto para situaciones
    como "stock insuficiente" o "el lote esta vencido": la peticion esta bien
    formada, pero no puede completarse con el estado actual de los datos.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "La operacion no se pudo completar."
    default_code = "business_error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict | None = None,
        status_code: int | None = None,
    ) -> None:
        self.business_code = code or self.default_code
        self.business_details = details
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message or self.default_detail)


def error_response(code: str, message: str | None = None, *, status_code: int, details=None):
    """Construye una respuesta de error con el mismo formato que el handler.

    Se usa en los pocos casos donde la vista necesita responder un error sin
    lanzar una excepcion, por ejemplo el login fallido: DRF convierte
    ``AuthenticationFailed`` en 403 cuando no hay cabecera de autenticacion,
    y aqui lo correcto es 401.
    """
    from rest_framework.response import Response

    return Response(
        {
            "error": {
                "code": code,
                "message": message or MESSAGES.get(code, MESSAGES["error"]),
                "details": details,
            }
        },
        status=status_code,
    )


def api_exception_handler(exc, context):
    """Normaliza cualquier excepcion de DRF al formato de error de my-pos."""
    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or exc.messages
        exc = ValidationError(detail=detail)

    response = drf_exception_handler(exc, context)
    if response is None:
        # Excepcion no manejada: se deja propagar para que Django la registre
        # y devuelva 500. Nunca se expone el detalle interno al cliente.
        return None

    if isinstance(exc, BusinessError):
        code = exc.business_code
        message = str(exc.detail)
        details = exc.business_details
    elif isinstance(exc, ValidationError):
        code = "validation_error"
        message = MESSAGES["validation_error"]
        details = exc.detail
    elif isinstance(exc, Throttled):
        code = "throttled"
        message = MESSAGES["throttled"]
        details = {"retry_after_seconds": exc.wait}
    else:
        code = getattr(exc, "default_code", None) or "error"
        message = MESSAGES.get(code, MESSAGES["error"])
        details = response.data

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return response
