import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "@/api/client";
import { authApi } from "@/api/endpoints/auth";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { TextField } from "@/components/Field";
import { Alert } from "@/components/Feedback";
import { useAuth } from "./context";

/**
 * Cambio de contrasena.
 *
 * Se usa en dos situaciones: el usuario la cambia por voluntad propia, o el
 * backend marco `must_change_password` porque un administrador la restablecio.
 */
export function ChangePasswordPage({ forced = false }: { forced?: boolean }) {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const isForced = forced || Boolean(user?.must_change_password);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError("La contrasena nueva debe tener al menos 8 caracteres.");
      return;
    }
    if (newPassword !== confirmation) {
      setError("La confirmacion no coincide con la contrasena nueva.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      await refresh();
      setSuccess(true);
      if (!isForced) {
        navigate("/", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card
        title="Cambiar contrasena"
        description={
          isForced
            ? "La administracion restablecio tu contrasena. Elige una nueva para continuar."
            : "Usa al menos 8 caracteres y evita datos personales."
        }
      >
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {isForced && !success && (
            <Alert tone="warning" title="Cambio obligatorio">
              No podras usar el sistema hasta que definas una contrasena propia.
            </Alert>
          )}
          {error && <Alert tone="danger">{error}</Alert>}
          {success && (
            <Alert tone="success" title="Contrasena actualizada">
              Ya puedes seguir trabajando con normalidad.
            </Alert>
          )}

          <TextField
            label="Contrasena actual"
            type="password"
            autoComplete="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
          />
          <TextField
            label="Contrasena nueva"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            hint="Minimo 8 caracteres."
            required
          />
          <TextField
            label="Repetir contrasena nueva"
            type="password"
            autoComplete="new-password"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            required
          />

          <div className="flex justify-end gap-2 pt-2">
            {!isForced && (
              <Button variant="secondary" onClick={() => navigate(-1)}>
                Cancelar
              </Button>
            )}
            <Button type="submit" loading={submitting}>
              Guardar contrasena
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
