"""Administracion de usuarios en Django Admin.

El admin es un respaldo operativo para gerencia, no la interfaz principal.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "full_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("last_name", "first_name")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email")}),
        (
            "Acceso",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "must_change_password",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    @admin.display(description="nombre")
    def full_name(self, obj: User) -> str:
        return obj.full_name
