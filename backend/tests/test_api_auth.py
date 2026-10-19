"""Pruebas del flujo de autenticacion por DNI y de la gestion de usuarios.

Se prueba la sesion real (cookie), no una simulacion: ``force_authenticate``
sirve para la matriz de permisos, pero aqui lo que se verifica es el ciclo
completo login -> cookie -> logout.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.audit.models import AuditAction, AuditEvent
from tests.factories import PASSWORD, make_user

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/v1/auth/login/"
CSRF_URL = "/api/v1/auth/csrf/"
ME_URL = "/api/v1/auth/me/"
LOGOUT_URL = "/api/v1/auth/logout/"


def csrf_client() -> APIClient:
    return APIClient(enforce_csrf_checks=True)


def fetch_csrf(client: APIClient) -> str:
    response = client.get(CSRF_URL)
    assert response.status_code == 200
    return response.data["csrfToken"]


def login(client: APIClient, username: str, password: str = PASSWORD):
    token = fetch_csrf(client)
    return client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )


def test_login_with_dni_returns_the_user_and_never_the_password(cashier_user):
    client = csrf_client()
    response = login(client, cashier_user.username)

    assert response.status_code == 200
    assert response.data["username"] == cashier_user.username
    assert response.data["role"] == Role.CAJERO
    assert "password" not in response.data
    assert "PruebaSegura123" not in str(response.data)

    # La sesion ya funciona.
    assert client.get(ME_URL).status_code == 200


def test_login_is_rejected_without_csrf_token(cashier_user):
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(
        LOGIN_URL,
        {"username": cashier_user.username, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 403


def test_login_with_wrong_password_is_generic(cashier_user):
    client = csrf_client()
    response = login(client, cashier_user.username, "clave-incorrecta")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "authentication_failed"
    # El mensaje no revela si el DNI existe o la contrasena es la que falla.
    assert "clave" not in response.data["error"]["message"].lower()

    assert AuditEvent.objects.filter(action=AuditAction.LOGIN_FAILED).count() == 1


def test_login_with_unknown_dni_gives_the_same_message(cashier_user):
    client = csrf_client()
    unknown = login(client, "99999999", "lo-que-sea")
    known = login(client, cashier_user.username, "lo-que-sea")

    assert unknown.status_code == known.status_code == 401
    assert unknown.data == known.data


def test_inactive_user_cannot_log_in(db):
    user = make_user("90000099", Role.CAJERO)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = login(csrf_client(), user.username)
    assert response.status_code == 401


def test_logout_really_invalidates_the_session(cashier_user):
    client = csrf_client()
    assert login(client, cashier_user.username).status_code == 200
    assert client.get(ME_URL).status_code == 200

    token = fetch_csrf(client)
    assert client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=token).status_code == 204
    assert client.get(ME_URL).status_code == 403


def test_deactivating_a_user_cuts_access_immediately(cashier_user, admin_user):
    client = csrf_client()
    assert login(client, cashier_user.username).status_code == 200

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)
    response = admin_client.post(f"/api/v1/users/{cashier_user.pk}/deactivate/")
    assert response.status_code == 200

    # La cookie sigue existiendo, pero el usuario ya no puede operar.
    assert client.get(ME_URL).status_code == 403


def test_me_reports_capabilities_by_role(cashier_user, auditor_user):
    cashier = APIClient()
    cashier.force_authenticate(user=cashier_user)
    capabilities = cashier.get(ME_URL).data["capabilities"]
    assert capabilities["can_sell"] is True
    assert capabilities["can_manage_users"] is False
    assert capabilities["can_view_dashboard"] is False

    auditor = APIClient()
    auditor.force_authenticate(user=auditor_user)
    capabilities = auditor.get(ME_URL).data["capabilities"]
    assert capabilities["can_sell"] is False
    assert capabilities["can_read_audit"] is True
    assert capabilities["can_view_all_sales"] is True


def test_password_change_requires_the_current_password_and_keeps_the_session(cashier_user):
    client = csrf_client()
    assert login(client, cashier_user.username).status_code == 200
    token = fetch_csrf(client)

    wrong = client.post(
        "/api/v1/auth/password/change/",
        {"current_password": "no-es", "new_password": "NuevaClave456"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert wrong.status_code == 400

    ok = client.post(
        "/api/v1/auth/password/change/",
        {"current_password": PASSWORD, "new_password": "NuevaClave456"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert ok.status_code == 200
    # No se expulsa al usuario: la sesion se renueva.
    assert client.get(ME_URL).status_code == 200

    cashier_user.refresh_from_db()
    assert cashier_user.check_password("NuevaClave456")
    assert AuditEvent.objects.filter(action=AuditAction.PASSWORD_CHANGED).exists()


def test_password_change_rejects_a_weak_password(cashier_user):
    client = csrf_client()
    assert login(client, cashier_user.username).status_code == 200
    token = fetch_csrf(client)

    response = client.post(
        "/api/v1/auth/password/change/",
        {"current_password": PASSWORD, "new_password": "12345678"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_admin_creates_a_user_and_the_password_never_comes_back(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(
        "/api/v1/users/",
        {
            "username": "90111222",
            "first_name": "Nueva",
            "last_name": "Cajera",
            "role": Role.CAJERO,
            "password": "ClaveSegura789",
            "must_change_password": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert "password" not in response.data
    assert "ClaveSegura789" not in str(response.data)

    created = User.objects.get(username="90111222")
    assert created.check_password("ClaveSegura789")
    assert created.must_change_password is True
    assert AuditEvent.objects.filter(action=AuditAction.USER_CREATED).exists()


def test_username_must_be_an_eight_digit_dni():
    from django.core.exceptions import ValidationError

    user = User(username="123", role=Role.CAJERO)
    with pytest.raises(ValidationError):
        user.full_clean()


def test_cannot_deactivate_the_last_active_admin(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(f"/api/v1/users/{admin_user.pk}/deactivate/")
    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.is_active is True


def test_admin_cannot_deactivate_their_own_user(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    # Hay dos administradores activos: el limite no es lo que bloquea.
    make_user("90000077", Role.ADMIN)

    response = client.post(f"/api/v1/users/{admin_user.pk}/deactivate/")
    assert response.status_code == 400


def test_role_change_is_audited(admin_user, cashier_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.post(
        f"/api/v1/users/{cashier_user.pk}/role/",
        {"role": Role.ALMACEN},
        format="json",
    )
    assert response.status_code == 200

    event = AuditEvent.objects.get(action=AuditAction.ROLE_CHANGED)
    assert event.before == {"role": Role.CAJERO}
    assert event.after == {"role": Role.ALMACEN}
