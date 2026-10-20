"""URLs del panel navegable de DRF.

La plantilla del panel resuelve ``rest_framework:login`` y
``rest_framework:logout``; este modulo publica esos nombres con vistas propias
que conservan el freno por IP y la auditoria del login de la API.
"""

from django.urls import path

from apps.accounts.views import PanelLoginView, PanelLogoutView

app_name = "rest_framework"

urlpatterns = [
    path("login/", PanelLoginView.as_view(), name="login"),
    path("logout/", PanelLogoutView.as_view(), name="logout"),
]
