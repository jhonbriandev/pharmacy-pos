import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Search, UserPlus, UserX } from "lucide-react";

import { errorMessage } from "@/api/client";
import { authApi, usersApi } from "@/api/endpoints/auth";
import type { Role, User } from "@/api/types";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card, PageHeader } from "@/components/Card";
import { Field, Input, Select } from "@/components/Field";
import { Alert, EmptyState, ErrorState, Spinner } from "@/components/Feedback";
import { Modal } from "@/components/Modal";
import { Pagination, Table, TBody, TD, TH, THead, TR, TableMessage } from "@/components/Table";
import { useAuth } from "@/features/auth/context";
import { formatDateTime } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";

const PAGE_SIZE = 25;

const ROLE_TONES: Record<Role, "success" | "info" | "warning" | "neutral" | "danger"> = {
  ADMIN: "danger",
  REGENTE: "info",
  CAJERO: "success",
  ALMACEN: "warning",
  AUDITOR: "neutral",
};

function NewUserModal({
  open,
  onClose,
  onSaved,
  roles,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  roles: Array<{ value: Role; label: string }>;
}) {
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("CAJERO");
  const [password, setPassword] = useState("");
  const [mustChange, setMustChange] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setUsername("");
    setFirstName("");
    setLastName("");
    setEmail("");
    setRole("CAJERO");
    setPassword("");
    setMustChange(true);
    setError(null);
  }, [open]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!/^\d{8}$/.test(username)) {
      setError("El usuario debe ser el DNI: exactamente 8 digitos.");
      return;
    }
    if (!firstName.trim() || !lastName.trim()) {
      setError("Nombres y apellidos son obligatorios.");
      return;
    }
    if (password.length < 8) {
      setError("La contrasena temporal debe tener al menos 8 caracteres.");
      return;
    }

    setSubmitting(true);
    try {
      await usersApi.create({
        username,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        role,
        password,
        must_change_password: mustChange,
      });
      onSaved();
      onClose();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Nuevo usuario"
      description="El DNI es el nombre de usuario. Nadie puede cambiar su DNI despues."
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="new-user-form" loading={submitting}>
            Crear usuario
          </Button>
        </>
      }
    >
      <form id="new-user-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="DNI" htmlFor="new-user-dni" required hint="8 digitos, sin puntos.">
            <Input
              id="new-user-dni"
              inputMode="numeric"
              maxLength={8}
              value={username}
              onChange={(event) => setUsername(event.target.value.replace(/\D/g, ""))}
              className="tracking-widest"
              required
            />
          </Field>
          <Field label="Rol" htmlFor="new-user-role" required>
            <Select
              id="new-user-role"
              value={role}
              onChange={(event) => setRole(event.target.value as Role)}
            >
              {roles.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Nombres" htmlFor="new-user-first" required>
            <Input
              id="new-user-first"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              maxLength={150}
              required
            />
          </Field>
          <Field label="Apellidos" htmlFor="new-user-last" required>
            <Input
              id="new-user-last"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
              maxLength={150}
              required
            />
          </Field>
          <Field label="Correo (opcional)" htmlFor="new-user-email" className="sm:col-span-2">
            <Input
              id="new-user-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="nombre@farmacia.pe"
            />
          </Field>
        </div>

        <Field
          label="Contrasena temporal"
          htmlFor="new-user-password"
          required
          hint="Minimo 8 caracteres. Se entrega en persona, nunca por correo."
        >
          <Input
            id="new-user-password"
            type="text"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </Field>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={mustChange}
            onChange={(event) => setMustChange(event.target.checked)}
            className="size-4 rounded border-slate-300"
          />
          Pedir cambio de contrasena al primer ingreso
        </label>
      </form>
    </Modal>
  );
}

function ResetPasswordModal({
  user,
  onClose,
}: {
  user: User | null;
  onClose: () => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!user) return;
    setPassword("");
    setError(null);
    setSuccess(false);
  }, [user]);

  if (!user) return null;

  const targetId = user.id;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("La contrasena debe tener al menos 8 caracteres.");
      return;
    }

    setSubmitting(true);
    try {
      await usersApi.resetPassword(targetId, password);
      setSuccess(true);
      setPassword("");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Restablecer contrasena"
      description={`${user.full_name} · DNI ${user.username}`}
      size="sm"
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cerrar
          </Button>
          <Button type="submit" form="reset-password-form" loading={submitting}>
            Restablecer
          </Button>
        </>
      }
    >
      <form id="reset-password-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        {success ? (
          <Alert tone="success" title="Contrasena restablecida">
            Comunicala en persona. El usuario debera cambiarla al ingresar.
          </Alert>
        ) : (
          <>
            <Alert tone="warning">
              Al restablecerla, el usuario debera cambiarla en su proximo ingreso.
            </Alert>
            <Field label="Nueva contrasena temporal" htmlFor="reset-password" required>
              <Input
                id="reset-password"
                type="text"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>
          </>
        )}
      </form>
    </Modal>
  );
}

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim(), 300);

  const [createOpen, setCreateOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<User | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, roleFilter]);

  const rolesQuery = useQuery({
    queryKey: ["roles"],
    queryFn: authApi.roles,
    staleTime: Infinity,
  });

  const usersQuery = useQuery({
    queryKey: ["users", { page, search: debouncedSearch, role: roleFilter }],
    queryFn: () =>
      usersApi.list({
        page,
        search: debouncedSearch || undefined,
        role: (roleFilter as Role) || "",
      }),
  });

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["users"] });
  }

  async function changeRole(user: User, role: Role) {
    setActionError(null);
    try {
      await usersApi.setRole(user.id, role);
      await refresh();
    } catch (caught) {
      setActionError(errorMessage(caught));
    }
  }

  async function confirmDeactivate() {
    if (!deactivateTarget) return;
    setActionError(null);
    try {
      await usersApi.deactivate(deactivateTarget.id);
      setDeactivateTarget(null);
      await refresh();
    } catch (caught) {
      setActionError(errorMessage(caught));
    }
  }

  const roles = rolesQuery.data ?? [];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Usuarios"
        description="El acceso se da por DNI y rol. Nadie se elimina: se desactiva."
        actions={
          <Button onClick={() => setCreateOpen(true)} icon={<UserPlus className="size-4" aria-hidden />}>
            Nuevo usuario
          </Button>
        }
      />

      {actionError && <Alert tone="danger">{actionError}</Alert>}

      <Card padded={false}>
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Buscar" htmlFor="users-search" className="lg:col-span-2">
            <div className="relative">
              <Search
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <Input
                id="users-search"
                placeholder="DNI, nombre o apellido…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="pl-9"
              />
            </div>
          </Field>
          <Field label="Rol" htmlFor="users-role">
            <Select
              id="users-role"
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value)}
            >
              <option value="">Todos</option>
              {roles.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        {usersQuery.isError ? (
          <div className="p-4">
            <ErrorState
              message={errorMessage(usersQuery.error)}
              onRetry={() => void usersQuery.refetch()}
            />
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <TH>DNI</TH>
                  <TH>Nombre</TH>
                  <TH>Rol</TH>
                  <TH>Estado</TH>
                  <TH>Ultimo acceso</TH>
                  <TH className="text-right">Acciones</TH>
                </tr>
              </THead>
              <TBody>
                {usersQuery.isLoading ? (
                  <TableMessage colSpan={6}>
                    <Spinner label="Cargando usuarios" />
                  </TableMessage>
                ) : usersQuery.data && usersQuery.data.results.length > 0 ? (
                  usersQuery.data.results.map((user) => {
                    const isSelf = user.id === currentUser?.id;
                    return (
                      <TR key={user.id}>
                        <TD className="font-mono font-medium text-slate-900">{user.username}</TD>
                        <TD>
                          <p className="font-medium text-slate-900">{user.full_name}</p>
                          {user.email && <p className="text-xs text-slate-500">{user.email}</p>}
                        </TD>
                        <TD>
                          {isSelf ? (
                            <Badge tone={ROLE_TONES[user.role]}>{user.role_display}</Badge>
                          ) : (
                            <Select
                              aria-label={`Rol de ${user.full_name}`}
                              value={user.role}
                              onChange={(event) => void changeRole(user, event.target.value as Role)}
                              className="h-9 text-sm"
                            >
                              {roles.map((option) => (
                                <option key={option.value} value={option.value}>
                                  {option.label}
                                </option>
                              ))}
                            </Select>
                          )}
                        </TD>
                        <TD>
                          {user.is_active ? (
                            <Badge tone="success">Activo</Badge>
                          ) : (
                            <Badge tone="neutral">Inactivo</Badge>
                          )}
                          {user.must_change_password && (
                            <Badge tone="warning" className="ml-1">
                              Cambio pendiente
                            </Badge>
                          )}
                        </TD>
                        <TD className="text-slate-500">
                          {user.last_login ? formatDateTime(user.last_login) : "Nunca"}
                        </TD>
                        <TD className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              title="Restablecer contrasena"
                              aria-label={`Restablecer contrasena de ${user.full_name}`}
                              onClick={() => setResetTarget(user)}
                              icon={<KeyRound className="size-4" aria-hidden />}
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              title="Desactivar usuario"
                              aria-label={`Desactivar a ${user.full_name}`}
                              disabled={!user.is_active || isSelf}
                              onClick={() => setDeactivateTarget(user)}
                              icon={<UserX className="size-4 text-slate-500" aria-hidden />}
                            />
                          </div>
                        </TD>
                      </TR>
                    );
                  })
                ) : (
                  <TableMessage colSpan={6}>
                    <EmptyState title="Sin usuarios" description="Crea el primero con «Nuevo usuario»." />
                  </TableMessage>
                )}
              </TBody>
            </Table>
            {usersQuery.data && (
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                count={usersQuery.data.count}
                onChange={setPage}
              />
            )}
          </>
        )}
      </Card>

      <NewUserModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSaved={() => void refresh()}
        roles={roles}
      />
      <ResetPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} />

      <Modal
        open={deactivateTarget !== null}
        onClose={() => setDeactivateTarget(null)}
        title="Desactivar usuario"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeactivateTarget(null)}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => void confirmDeactivate()}>
              Desactivar
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-700">
          {deactivateTarget?.full_name} dejara de poder iniciar sesion de inmediato. Su historial de
          ventas y movimientos se conserva.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          No se elimina la cuenta: desactivar es reversible, borrar no.
        </p>
      </Modal>
    </div>
  );
}
