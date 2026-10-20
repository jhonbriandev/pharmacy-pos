"""Pruebas del login/logout del panel navegable de DRF.

El panel no debe ser una puerta trasera: reutiliza la sesion de la aplicacion y
conserva el limite de intentos por IP y la auditoria del login de la API.
"""

from django.core.cache import cache

from apps.audit.models import AuditAction, AuditEvent
from tests.base import BaseAPITestCase
from tests.factories import PASSWORD

PANEL_LOGIN_URL = "/api-auth/login/"
PANEL_LOGOUT_URL = "/api-auth/logout/"
ME_URL = "/api/v1/auth/me/"

# El cliente de DRF usa JSON por defecto (TEST_REQUEST_DEFAULT_FORMAT); el
# formulario del panel es un POST de navegador, que Django lee de request.POST.
FORM = "multipart"


class PanelLoginTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        # El freno usa la cache por defecto; limpiarla aisla cada prueba.
        cache.clear()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_login_page_renders_the_drf_form(self):
        response = self.client.get(PANEL_LOGIN_URL)

        self.assertEqual(response.status_code, 200)
        # La plantilla del panel (rest_framework/login.html) se renderiza con
        # sus estaticos; si faltara el template o el namespace, seria un 500.
        self.assertContains(response, "<form")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_credentials_open_the_same_session_and_are_audited(self):
        response = self.client.post(
            PANEL_LOGIN_URL,
            {"username": self.cashier_user.username, "password": PASSWORD},
            format=FORM,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(ME_URL).status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditAction.LOGIN_SUCCESS, actor=self.cashier_user
            ).exists()
        )

    def test_invalid_credentials_are_audited_and_do_not_open_a_session(self):
        response = self.client.post(
            PANEL_LOGIN_URL,
            {"username": self.cashier_user.username, "password": "incorrecta"},
            format=FORM,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(ME_URL).status_code, 403)
        self.assertTrue(AuditEvent.objects.filter(action=AuditAction.LOGIN_FAILED).exists())

    def test_repeated_failures_are_throttled_per_ip(self):
        for _ in range(10):
            self.client.post(
                PANEL_LOGIN_URL,
                {"username": self.cashier_user.username, "password": "incorrecta"},
                format=FORM,
            )

        blocked = self.client.post(
            PANEL_LOGIN_URL,
            {"username": self.cashier_user.username, "password": PASSWORD},
            format=FORM,
        )

        self.assertEqual(blocked.status_code, 429)
        # Ni con la contrasena correcta entra mientras dura el freno.
        self.assertEqual(self.client.get(ME_URL).status_code, 403)

    def test_logout_from_the_panel_is_audited(self):
        self.client.force_login(self.cashier_user)

        response = self.client.post(PANEL_LOGOUT_URL, {"next": "/api/v1/"}, format=FORM)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(ME_URL).status_code, 403)
        self.assertTrue(
            AuditEvent.objects.filter(action=AuditAction.LOGOUT, actor=self.cashier_user).exists()
        )
