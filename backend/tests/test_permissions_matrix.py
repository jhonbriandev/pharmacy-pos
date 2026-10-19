"""Matriz de permisos: cada endpoint contra cada rol.

Un agujero de permisos no se nota mirando la interfaz: se nota aqui. Por eso
cada endpoint de la API esta declarado en esta matriz y se prueba con todos los
roles. Si alguien agrega un endpoint y olvida declararlo, la prueba de
exhaustividad falla y obliga a decidir explicitamente quien puede usarlo.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role

pytestmark = pytest.mark.django_db

ROLES = [Role.ADMIN, Role.REGENTE, Role.CAJERO, Role.ALMACEN, Role.AUDITOR]

# Endpoints y los roles que deben poder acceder.
# "read" = metodos seguros; "write" = metodos que modifican datos.
MATRIX = {
    "auth/me/": {"read": set(ROLES)},
    "roles/": {"read": set(ROLES)},
    "meta/": {"read": set(ROLES)},
    "products/": {"read": set(ROLES), "write": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "product-groups/": {"read": set(ROLES), "write": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "laboratories/": {"read": set(ROLES), "write": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "categories/": {"read": set(ROLES), "write": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "active-ingredients/": {"read": set(ROLES), "write": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "unit-conversions/": {"read": set(ROLES), "write": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "stock-entries/": {"read": {Role.ADMIN, Role.REGENTE, Role.ALMACEN}},
    "stock-movements/": {"read": {Role.ADMIN, Role.REGENTE, Role.ALMACEN, Role.AUDITOR}},
    "lots/": {"read": {Role.ADMIN, Role.REGENTE, Role.ALMACEN, Role.AUDITOR}},
    "sales/": {"read": {Role.ADMIN, Role.REGENTE, Role.CAJERO, Role.AUDITOR}},
    "audit-events/": {"read": {Role.ADMIN, Role.AUDITOR}},
    "reports/dashboard/": {"read": {Role.ADMIN, Role.REGENTE}},
    "reports/exports/sales.csv": {"read": {Role.ADMIN, Role.REGENTE}},
    "inventory/consistency/": {"read": {Role.ADMIN}},
    "users/": {"read": {Role.ADMIN}, "write": {Role.ADMIN}},
}

# Endpoints POST que no son CRUD de recurso.
POST_ENDPOINTS = {
    "stock-adjustments/": {Role.ADMIN, Role.REGENTE},
    "stock-fractionations/": {Role.ADMIN, Role.REGENTE, Role.ALMACEN},
    "sales/": {Role.ADMIN, Role.REGENTE, Role.CAJERO},
}


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def users(db):
    from tests.factories import make_user

    return {role: make_user(f"8000{index:04d}", role) for index, role in enumerate(ROLES, start=1)}


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("path", sorted(MATRIX))
def test_read_access_matrix(users, role, path):
    client = _client_for(users[role])
    response = client.get(f"/api/v1/{path}")
    expected = role in MATRIX[path]["read"]
    if expected:
        assert response.status_code != 403, f"{role} deberia leer {path}"
    else:
        assert response.status_code == 403, f"{role} NO deberia leer {path}"


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("path", sorted(MATRIX))
def test_write_access_matrix(users, role, path):
    allowed_roles = MATRIX[path].get("write")
    if allowed_roles is None:
        pytest.skip("Endpoint sin escritura CRUD")
    client = _client_for(users[role])
    response = client.post(f"/api/v1/{path}", {}, format="json")
    expected = role in allowed_roles
    if expected:
        # Puede fallar la validacion (400) pero nunca por permisos.
        assert response.status_code != 403
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("path", sorted(POST_ENDPOINTS))
def test_action_endpoints_matrix(users, role, path):
    client = _client_for(users[role])
    response = client.post(f"/api/v1/{path}", {}, format="json")
    expected = role in POST_ENDPOINTS[path]
    if expected:
        assert response.status_code != 403
    else:
        assert response.status_code == 403


def test_anonymous_cannot_access_protected_endpoints():
    client = APIClient()
    for path in ("auth/me/", "products/", "sales/", "users/", "reports/dashboard/"):
        response = client.get(f"/api/v1/{path}")
        assert response.status_code == 403, f"{path} deberia exigir autenticacion"


def test_every_registered_api_route_is_declared_in_the_matrix():
    """Exhaustividad: una ruta nueva sin declarar rompe la CI.

    Evita que un endpoint nuevo quede accesible para todos por descuido.
    """
    declared = {f"/api/v1/{path}" for path in MATRIX}
    declared |= {f"/api/v1/{path}" for path in POST_ENDPOINTS}

    known_exceptions = {
        "/api/v1/auth/csrf/",
        "/api/v1/auth/login/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/password/change/",
        "/api/v1/users/<int:pk>/",
        "/api/v1/users/<int:pk>/deactivate/",
        "/api/v1/users/<int:pk>/role/",
        "/api/v1/users/<int:pk>/reset-password/",
        "/api/v1/receipts/<str:number>/",
        "/api/v1/reports/sales-summary/",
        "/api/v1/reports/top-products/",
        "/api/v1/reports/exports/movements.csv",
        "/api/v1/lots/expiring/",
        "/api/v1/lots/expired/",
        "/api/v1/lots/<int:pk>/block/",
        "/api/v1/products/lookup/",
        "/api/v1/products/low-stock/",
        "/api/v1/products/<int:pk>/lots/",
        "/api/v1/sales/<int:pk>/receipt/",
    }

    api_routes = _api_routes()
    declared_normalized = {_normalize(path) for path in declared | known_exceptions}

    undeclared = [
        route
        for route in api_routes
        if not any(route == path or route.startswith(path) for path in declared_normalized)
    ]
    assert not undeclared, (
        "Estas rutas de la API no estan declaradas en la matriz de permisos:\n"
        + "\n".join(sorted(undeclared))
    )


def _normalize(route: str) -> str:
    """Quita los anclajes de regex que Django agrega a los patrones."""
    return route.replace("^", "").replace("$", "")


def _api_routes() -> set[str]:
    """Rutas resueltas bajo /api/v1/, sin las variantes de formato.

    Los detalles (``/sales/<pk>/``) cuelgan de su coleccion ya declarada, asi
    que se consideran cubiertos por prefijo.
    """
    from django.urls import get_resolver
    from django.urls.resolvers import URLResolver

    routes: set[str] = set()

    def walk(patterns, prefix: str) -> None:
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, route)
            else:
                routes.add(_normalize("/" + route))

    walk(get_resolver().url_patterns, "")

    return {
        route
        for route in routes
        if route.startswith("/api/v1/") and route != "/api/v1/" and "format" not in route
    }
