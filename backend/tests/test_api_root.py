"""Pruebas del indice de la API (punto de entrada del panel navegable de DRF).

El indice resuelve con ``reverse`` las rutas que anuncia. Si alguien renombra
una ruta y olvida el indice, esta prueba falla (``NoReverseMatch`` -> 500) y
evita publicar un panel roto.

El panel navegable es una decision de *settings* (ver docs/decisiones.md, D22):
DRF fija los renderers cuando importa la vista, asi que no se puede simular con
``override_settings``. Por eso la ultima prueba importa el modulo de produccion
y comprueba que JSON sigue yendo primero.
"""

import importlib
import os
from unittest import mock

from django.test import SimpleTestCase

from tests.base import BaseAPITestCase

API_ROOT_URL = "/api/v1/"


class ApiRootTests(BaseAPITestCase):
    def test_root_is_available_to_authenticated_users(self):
        response = self.api_for(self.admin_user).get(API_ROOT_URL)

        self.assertEqual(response.status_code, 200)
        self.assertIn("autenticacion", response.data)
        self.assertIn("catalogo", response.data)
        self.assertIn("inventario", response.data)
        self.assertIn("ventas", response.data)

    def test_root_announced_paths_exist(self):
        """Cada ruta anunciada sigue en pie (no 404 para un GET de lectura)."""
        data = self.api_for(self.admin_user).get(API_ROOT_URL).data

        for group in data.values():
            for url in group.values():
                with self.subTest(url=url):
                    response = self.api_for(self.admin_user).get(url)
                    self.assertNotEqual(response.status_code, 404)

    def test_root_requires_authentication(self):
        response = self.client.get(API_ROOT_URL)

        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)


class ProductionApiSettingsTests(SimpleTestCase):
    def test_production_keeps_json_before_the_browsable_panel(self):
        # Importar el modulo de produccion lee variables de entorno; se fija una
        # que siempre debe valer False fuera de desarrollo.
        with mock.patch.dict(os.environ, {"DJANGO_DEBUG": "False"}):
            module = importlib.import_module("config.settings.prod")

        renderers = module.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"]

        self.assertEqual(renderers[0], "rest_framework.renderers.JSONRenderer")
        self.assertIn("rest_framework.renderers.BrowsableAPIRenderer", renderers)

    def test_production_redirects_the_panel_login_to_the_api_index(self):
        with mock.patch.dict(os.environ, {"DJANGO_DEBUG": "False"}):
            module = importlib.import_module("config.settings.prod")

        self.assertEqual(module.LOGIN_REDIRECT_URL, "/api/v1/")
        self.assertEqual(module.LOGOUT_REDIRECT_URL, "/api/v1/")
