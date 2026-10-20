"""Vistas de autenticacion y gestion de usuarios.

Decisiones relevantes (ver docs/decisiones.md):
  - La sesion vive en una cookie HttpOnly: cerrar sesion la invalida en el
    servidor de verdad, cosa que un JWT no garantiza sin listas de revocacion.
  - Desactivar un usuario corta su acceso de inmediato.
  - El login exige token CSRF: el frontend llama antes a ``/auth/csrf/``.
"""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.core.cache import cache
from django.db.models import Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsAdmin
from apps.accounts.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    RoleUpdateSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.audit.models import AuditAction
from apps.audit.services import get_client_ip, record_event
from apps.common.exceptions import error_response
from apps.common.pagination import StandardResultsSetPagination

User = get_user_model()

MAX_FAILED_ATTEMPTS_HINT = "Demasiados intentos fallidos. Espera un momento antes de reintentar."

# Mismo limite que DEFAULT_THROTTLE_RATES["login"] (10/min), aplicado a la vista
# de login del panel navegable (que es una vista de Django, no de DRF).
PANEL_LOGIN_MAX_ATTEMPTS = 10
PANEL_LOGIN_WINDOW_SECONDS = 60


class CsrfView(APIView):
    """Entrega el token CSRF y garantiza que la cookie exista.

    El frontend lo llama al arrancar. La cookie no es HttpOnly (el navegador la
    envia en el header X-CSRFToken); la de sesion si lo es.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """Inicio de sesion por DNI."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dni = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]

        user = authenticate(request, username=dni, password=password)
        if user is None:
            record_event(
                action=AuditAction.LOGIN_FAILED,
                actor=None,
                after={"username": dni},
                request=request,
            )
            # Mensaje generico: no revela si el DNI existe o si la contrasena
            # es lo que falla.
            return error_response("authentication_failed", status_code=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity=user,
            actor=user,
            request=request,
        )
        return Response(UserSerializer(user).data)


class PanelLoginView(DjangoLoginView):
    """Login del panel navegable de DRF.

    Usa la misma sesion y el mismo usuario que la aplicacion (username = DNI),
    pero conserva las defensas del login de la API: limite de intentos por IP y
    evento de auditoria. No se delega en ``rest_framework.urls`` porque esa
    vista de Django no tiene throttling ni deja rastro en la auditoria.
    """

    template_name = "rest_framework/login.html"
    redirect_authenticated_user = True

    def _throttle_key(self) -> str:
        ip = get_client_ip(self.request) or "desconocida"
        return f"mypos:panel-login:{ip}"

    def dispatch(self, request, *args, **kwargs):
        if (
            request.method == "POST"
            and cache.get(self._throttle_key(), 0) >= PANEL_LOGIN_MAX_ATTEMPTS
        ):
            return HttpResponse(
                "Demasiados intentos fallidos. Espera un minuto antes de reintentar.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self._throttle_key()
        # cache.incr falla si la clave expiro entre el get y el incr.
        if cache.add(key, 1, PANEL_LOGIN_WINDOW_SECONDS) is False:
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, PANEL_LOGIN_WINDOW_SECONDS)
        record_event(
            action=AuditAction.LOGIN_FAILED,
            actor=None,
            after={"username": form.data.get("username", "")},
            request=self.request,
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._throttle_key())
        user = form.get_user()
        record_event(
            action=AuditAction.LOGIN_SUCCESS,
            entity=user,
            actor=user,
            request=self.request,
        )
        return super().form_valid(form)


class PanelLogoutView(DjangoLogoutView):
    """Cierre de sesion desde el panel, auditado como el de la API."""

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            record_event(
                action=AuditAction.LOGOUT,
                entity=request.user,
                actor=request.user,
                request=request,
            )
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """Cierre de sesion: invalida la sesion en el servidor."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        record_event(
            action=AuditAction.LOGOUT,
            entity=request.user,
            actor=request.user,
            request=request,
        )
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Usuario actual y sus capacidades, para que la UI adapte el menu."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                **UserSerializer(user).data,
                "capabilities": {
                    "can_sell": user.role in (Role.ADMIN, Role.REGENTE, Role.CAJERO),
                    "can_manage_inventory": user.role in (Role.ADMIN, Role.REGENTE, Role.ALMACEN),
                    "can_manage_catalog": user.role in (Role.ADMIN, Role.REGENTE, Role.ALMACEN),
                    "can_manage_users": user.role == Role.ADMIN,
                    "can_view_dashboard": user.role in (Role.ADMIN, Role.REGENTE),
                    "can_view_all_sales": user.role in (Role.ADMIN, Role.REGENTE, Role.AUDITOR),
                    "can_read_audit": user.role in (Role.ADMIN, Role.AUDITOR),
                },
            }
        )


class PasswordChangeView(APIView):
    """Cambio de contrasena por el propio usuario."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])

        record_event(
            action=AuditAction.PASSWORD_CHANGED,
            entity=user,
            actor=user,
            request=request,
        )
        # Al cambiar la contrasena, Django invalida la sesion: se vuelve a
        # iniciar con la nueva credencial para no expulsar al usuario.
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"detail": "Contrasena actualizada correctamente."})


class UserListCreateView(APIView):
    """Listado y creacion de usuarios. Solo administracion."""

    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = User.objects.all().order_by("last_name", "first_name")
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in {"1", "true", "yes"})
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )
        # El sobre paginado es el contrato de todos los listados de la API
        # (ver docs/api.md); la pantalla de usuarios espera {count, results}.
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        record_event(
            action=AuditAction.USER_CREATED,
            entity=user,
            actor=request.user,
            after={
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
            },
            request=request,
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    """Detalle, edicion, desactivacion, cambio de rol y reseteo de contrasena."""

    permission_classes = [IsAdmin]

    def get_object(self, pk: int):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist as exc:
            raise ValidationError({"detail": "El usuario no existe."}) from exc

    def get(self, request, pk: int):
        return Response(UserSerializer(self.get_object(pk)).data)

    def patch(self, request, pk: int):
        user = self.get_object(pk)
        before = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }

        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        after = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
        record_event(
            action=AuditAction.USER_UPDATED,
            entity=user,
            actor=request.user,
            before=before,
            after=after,
            request=request,
        )
        return Response(UserSerializer(user).data)


class UserDeactivateView(APIView):
    """Desactiva un usuario sin borrarlo: su historial se conserva."""

    permission_classes = [IsAdmin]

    def post(self, request, pk: int):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist as exc:
            raise ValidationError({"detail": "El usuario no existe."}) from exc

        if user.pk == request.user.pk:
            raise ValidationError({"detail": "No puedes desactivar tu propio usuario."})

        if user.role == Role.ADMIN and user.is_active:
            active_admins = User.objects.filter(role=Role.ADMIN, is_active=True).count()
            if active_admins <= 1:
                raise ValidationError(
                    {"detail": "No se puede desactivar al ultimo administrador activo."}
                )

        user.is_active = False
        user.save(update_fields=["is_active"])

        record_event(
            action=AuditAction.USER_DEACTIVATED,
            entity=user,
            actor=request.user,
            before={"is_active": True},
            after={"is_active": False},
            request=request,
        )
        return Response(UserSerializer(user).data)


class UserRoleUpdateView(APIView):
    """Cambio de rol, auditado como accion sensible."""

    permission_classes = [IsAdmin]

    def post(self, request, pk: int):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist as exc:
            raise ValidationError({"detail": "El usuario no existe."}) from exc

        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        if user.role == Role.ADMIN and new_role != Role.ADMIN:
            active_admins = User.objects.filter(role=Role.ADMIN, is_active=True).count()
            if active_admins <= 1:
                raise ValidationError(
                    {"detail": "No se puede quitar el rol al ultimo administrador activo."}
                )

        previous_role = user.role
        user.role = new_role
        user.save(update_fields=["role"])

        record_event(
            action=AuditAction.ROLE_CHANGED,
            entity=user,
            actor=request.user,
            before={"role": previous_role},
            after={"role": new_role},
            request=request,
        )
        return Response(UserSerializer(user).data)


class UserPasswordResetView(APIView):
    """Restablece la contrasena de un usuario (sin enviar correo)."""

    permission_classes = [IsAdmin]

    def post(self, request, pk: int):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist as exc:
            raise ValidationError({"detail": "El usuario no existe."}) from exc

        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password"])

        record_event(
            action=AuditAction.PASSWORD_RESET,
            entity=user,
            actor=request.user,
            request=request,
        )
        return Response({"detail": "Contrasena restablecida. El usuario debera cambiarla."})


class RoleListView(APIView):
    """Catalogo de roles con su descripcion, para los formularios."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([{"value": value, "label": label} for value, label in Role.choices])
