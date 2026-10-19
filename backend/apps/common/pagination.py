"""Paginacion estandar de la API."""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Paginacion por numero de pagina, con tamano configurable acotado.

    El limite superior evita que un cliente pida la tabla completa y tumbe la
    instancia gratuita del servidor.
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
