"""Pruebas del flujo de autenticacion por DNI y de la gestion de usuarios.

Se prueba la sesion real (cookie), no una simulacion: ``force_authenticate``
sirve para la matriz de permisos, pero aqui lo que se verifica es el ciclo
completo login -> cookie -> logout.
"""

from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.audit.models import AuditAction, AuditEvent
from tests.base import BaseAPITestCase
from tests.factories import PASSWORD, UserFactory

LOGIN_URL = "/api/v1/auth/login/"
CSRF_URL = "/api/v1/auth/csrf/"
ME_URL = "/api/v1/auth/me/"
LOGOUT_URL = "/api/v1/auth/logout/"


class AuthApiTests(BaseAPITestCase):
    def csrf_client(self):
        return APIClient(enforce_csrf_checks=True)

    def fetch_csrf(self, client):
        response = client.get(CSRF_URL)
        self.assertEqual(response.status_code, 200)
        return response.data["csrfToken"]

    def login(self, client, username, password=PASSWORD):
        token = self.fetch_csrf(client)
        return client.post(
            LOGIN_URL,
            {"username": username, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

    def test_login_with_dni_returns_the_user_and_never_the_password(self):
        client = self.csrf_client()
        response = self.login(client, self.cashier_user.username)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], self.cashier_user.username)
        self.assertEqual(response.data["role"], Role.CAJERO)
        self.assertNotIn("password", response.data)
        self.assertNotIn(PASSWORD, str(response.data))

        # La sesion ya funciona.
        self.assertEqual(client.get(ME_URL).status_code, 200)

    def test_login_is_rejected_without_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            LOGIN_URL,
            {"username": self.cashier_user.username, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_with_wrong_password_is_generic(self):
        client = self.csrf_client()
        response = self.login(client, self.cashier_user.username, "clave-incorrecta")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["error"]["code"], "authentication_failed")
        # El mensaje no revela si el DNI existe o la contrasena es la que falla.
        self.assertNotIn("clave", response.data["error"]["message"].lower())

        self.assertEqual(AuditEvent.objects.filter(action=AuditAction.LOGIN_FAILED).count(), 1)

    def test_login_with_unknown_dni_gives_the_same_message(self):
        client = self.csrf_client()
        unknown = self.login(client, "99999999", "lo-que-sea")
        known = self.login(client, self.cashier_user.username, "lo-que-sea")

        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(unknown.data, known.data)

    def test_inactive_user_cannot_log_in(self):
        user = UserFactory(role=Role.CAJERO, is_active=False)

        response = self.login(self.csrf_client(), user.username)
        self.assertEqual(response.status_code, 401)

    def test_logout_really_invalidates_the_session(self):
        client = self.csrf_client()
        self.assertEqual(self.login(client, self.cashier_user.username).status_code, 200)
        self.assertEqual(client.get(ME_URL).status_code, 200)

        token = self.fetch_csrf(client)
        self.assertEqual(client.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(client.get(ME_URL).status_code, 403)

    def test_deactivating_a_user_cuts_access_immediately(self):
        client = self.csrf_client()
        self.assertEqual(self.login(client, self.cashier_user.username).status_code, 200)

        response = self.api_for(self.admin_user).post(
            f"/api/v1/users/{self.cashier_user.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, 200)

        # La cookie sigue existiendo, pero el usuario ya no puede operar.
        self.assertEqual(client.get(ME_URL).status_code, 403)

    def test_me_reports_capabilities_by_role(self):
        capabilities = self.api_for(self.cashier_user).get(ME_URL).data["capabilities"]
        self.assertTrue(capabilities["can_sell"])
        self.assertFalse(capabilities["can_manage_users"])
        self.assertFalse(capabilities["can_view_dashboard"])

        capabilities = self.api_for(self.auditor_user).get(ME_URL).data["capabilities"]
        self.assertFalse(capabilities["can_sell"])
        self.assertTrue(capabilities["can_read_audit"])
        self.assertTrue(capabilities["can_view_all_sales"])

    def test_password_change_requires_the_current_password_and_keeps_the_session(self):
        client = self.csrf_client()
        self.assertEqual(self.login(client, self.cashier_user.username).status_code, 200)
        token = self.fetch_csrf(client)

        wrong = client.post(
            "/api/v1/auth/password/change/",
            {"current_password": "no-es", "new_password": "NuevaClave456"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(wrong.status_code, 400)

        ok = client.post(
            "/api/v1/auth/password/change/",
            {"current_password": PASSWORD, "new_password": "NuevaClave456"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(ok.status_code, 200)
        # No se expulsa al usuario: la sesion se renueva.
        self.assertEqual(client.get(ME_URL).status_code, 200)

        self.cashier_user.refresh_from_db()
        self.assertTrue(self.cashier_user.check_password("NuevaClave456"))
        self.assertTrue(AuditEvent.objects.filter(action=AuditAction.PASSWORD_CHANGED).exists())

    def test_password_change_rejects_a_weak_password(self):
        client = self.csrf_client()
        self.assertEqual(self.login(client, self.cashier_user.username).status_code, 200)
        token = self.fetch_csrf(client)

        response = client.post(
            "/api/v1/auth/password/change/",
            {"current_password": PASSWORD, "new_password": "12345678"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")

    def test_admin_creates_a_user_and_the_password_never_comes_back(self):
        response = self.api_for(self.admin_user).post(
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
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.data)
        self.assertNotIn("ClaveSegura789", str(response.data))

        created = User.objects.get(username="90111222")
        self.assertTrue(created.check_password("ClaveSegura789"))
        self.assertTrue(created.must_change_password)
        self.assertTrue(AuditEvent.objects.filter(action=AuditAction.USER_CREATED).exists())

    def test_username_must_be_an_eight_digit_dni(self):
        user = User(username="123", role=Role.CAJERO)
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_cannot_deactivate_the_last_active_admin(self):
        response = self.api_for(self.admin_user).post(
            f"/api/v1/users/{self.admin_user.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, 400)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)

    def test_admin_cannot_deactivate_their_own_user(self):
        # Hay dos administradores activos: el limite no es lo que bloquea.
        UserFactory(role=Role.ADMIN)

        response = self.api_for(self.admin_user).post(
            f"/api/v1/users/{self.admin_user.pk}/deactivate/"
        )
        self.assertEqual(response.status_code, 400)

    def test_role_change_is_audited(self):
        response = self.api_for(self.admin_user).post(
            f"/api/v1/users/{self.cashier_user.pk}/role/",
            {"role": Role.ALMACEN},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        event = AuditEvent.objects.get(action=AuditAction.ROLE_CHANGED)
        self.assertEqual(event.before, {"role": Role.CAJERO})
        self.assertEqual(event.after, {"role": Role.ALMACEN})

    def test_user_list_returns_the_paginated_envelope(self):
        response = self.api_for(self.admin_user).get("/api/v1/users/")

        self.assertEqual(response.status_code, 200)
        for key in ("count", "results", "next", "previous"):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["count"], User.objects.count())
        self.assertIsInstance(response.data["results"], list)
        self.assertNotIn("password", response.data["results"][0])

    def test_user_list_can_filter_by_role_and_search(self):
        client = self.api_for(self.admin_user)

        by_role = client.get("/api/v1/users/", {"role": Role.CAJERO})
        self.assertEqual(by_role.status_code, 200)
        self.assertTrue(by_role.data["results"])
        self.assertTrue(all(row["role"] == Role.CAJERO for row in by_role.data["results"]))

        by_search = client.get("/api/v1/users/", {"search": self.cashier_user.username})
        self.assertEqual(by_search.status_code, 200)
        self.assertEqual(
            [row["username"] for row in by_search.data["results"]],
            [self.cashier_user.username],
        )
