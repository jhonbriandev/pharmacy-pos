"""Serializers de usuarios y autenticacion.

Regla: la contrasena nunca sale de la API. Ni en el detalle, ni en el listado,
ni en los errores.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import Role

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Datos publicos del usuario (nunca incluye contrasena)."""

    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "role",
            "role_display",
            "is_active",
            "must_change_password",
            "last_login",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "password",
            "must_change_password",
        )

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Actualizacion de datos. El rol se cambia por un endpoint auditado."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contrasena actual no es correcta.")
        return value

    def validate_new_password(self, value: str) -> str:
        validate_password(value, self.context["request"].user)
        return value


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=8, help_text="DNI del usuario.")
    password = serializers.CharField(write_only=True)
