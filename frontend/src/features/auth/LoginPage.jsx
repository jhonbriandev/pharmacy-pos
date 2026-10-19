import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { KeyRound, ShieldCheck, UserRound } from "lucide-react";
import { errorMessage } from "@/api/client";
import { Alert } from "@/components/Feedback";
import { Button } from "@/components/Button";
import { Field, Input } from "@/components/Field";
import { useAuth } from "./context";
export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [dni, setDni] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const isDevelopment = import.meta.env.VITE_APP_ENV === "development";
  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    if (!/^\d{8}$/.test(dni)) {
      setError("El usuario es tu DNI: 8 digitos, sin espacios.");
      return;
    }
    if (!password) {
      setError("Ingresa tu contrasena.");
      return;
    }
    setSubmitting(true);
    try {
      await login(dni, password);
      const from = location.state?.from;
      navigate(from && from !== "/login" ? from : "/", {
        replace: true,
      });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      {/* Panel de marca: solo visible en pantallas grandes. */}
      <section className="hidden flex-col justify-between bg-brand-800 p-12 text-brand-50 lg:flex">
        <div>
          <p className="text-sm font-semibold tracking-[0.2em] uppercase">my-pos</p>
          <h1 className="mt-6 max-w-md text-4xl leading-tight font-semibold text-white">
            Punto de venta e inventario para farmacia
          </h1>
          <p className="mt-4 max-w-md text-brand-100">
            Ventas con trazabilidad por lote y vencimiento, control de stock y reportes para
            gerencia.
          </p>
        </div>

        <ul className="space-y-3 text-sm text-brand-100">
          <li className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
            Cada movimiento de stock queda registrado y no se puede editar.
          </li>
          <li className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
            La venta se descuenta del lote que vence primero (FEFO).
          </li>
          <li className="flex items-start gap-2">
            <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
            Un lote vencido no se puede vender, ni siquiera el mismo dia siguiente.
          </li>
        </ul>

        <p className="text-xs text-brand-200">
          Precios en soles con IGV incluido · Zona horaria America/Lima
        </p>
      </section>

      <section className="flex items-center justify-center bg-slate-50 px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden">
            <p className="text-sm font-semibold tracking-[0.2em] text-brand-700 uppercase">
              my-pos
            </p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-900">Iniciar sesion</h1>
          </div>

          <div className="hidden lg:block">
            <h2 className="text-2xl font-semibold text-slate-900">Iniciar sesion</h2>
            <p className="mt-1 text-sm text-slate-500">Accede con tu DNI y contrasena.</p>
          </div>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
            {error && <Alert tone="danger">{error}</Alert>}

            <Field
              label="DNI"
              htmlFor="username"
              required
              hint="8 digitos, sin puntos ni espacios."
            >
              <div className="relative">
                <UserRound
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <Input
                  id="username"
                  name="username"
                  inputMode="numeric"
                  autoComplete="username"
                  autoFocus
                  maxLength={8}
                  placeholder="12345678"
                  value={dni}
                  onChange={(event) => setDni(event.target.value.replace(/\D/g, ""))}
                  className="pl-9 tracking-widest"
                  required
                />
              </div>
            </Field>

            <Field label="Contrasena" htmlFor="password" required>
              <div className="relative">
                <KeyRound
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <Input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </Field>

            <Button type="submit" fullWidth size="lg" loading={submitting}>
              Entrar
            </Button>
          </form>

          <p className="mt-6 text-xs text-slate-500">
            Si olvidaste tu contrasena, pide a la administracion que la restablezca. Por seguridad,
            el sistema no envia correos.
          </p>

          {isDevelopment && (
            <Alert tone="info" title="Entorno de desarrollo" className="mt-6">
              <p>
                Usuarios de demostracion del <code>seed</code>: DNI <strong>10000001</strong>{" "}
                (administracion) a <strong>10000006</strong> (auditoria). Contrasena{" "}
                <strong>Farmacia2026</strong>.
              </p>
            </Alert>
          )}
        </div>
      </section>
    </main>
  );
}
