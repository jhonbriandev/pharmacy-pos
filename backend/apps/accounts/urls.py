"""Rutas de autenticacion y usuarios."""

from django.urls import path

from apps.accounts.views import (
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RoleListView,
    UserDeactivateView,
    UserDetailView,
    UserListCreateView,
    UserPasswordResetView,
    UserRoleUpdateView,
)

app_name = "accounts"

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="csrf"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<int:pk>/deactivate/", UserDeactivateView.as_view(), name="user-deactivate"),
    path("users/<int:pk>/role/", UserRoleUpdateView.as_view(), name="user-role"),
    path(
        "users/<int:pk>/reset-password/",
        UserPasswordResetView.as_view(),
        name="user-reset-password",
    ),
    path("roles/", RoleListView.as_view(), name="role-list"),
]
