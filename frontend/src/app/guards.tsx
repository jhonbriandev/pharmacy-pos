import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";

import type { Capabilities } from "@/api/types";
import { useAuth } from "@/features/auth/context";
import { homePathFor } from "./navigation";

function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center gap-2 text-sm text-slate-500">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      Cargando…
    </div>
  );
}

/**
 * Puerta de entrada a la aplicacion.
 *
 * Mientras se consulta la sesion no se redirige: hacerlo expulsaria a un
 * usuario valido en cada recarga por una simple carrera de tiempos.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) return <FullPageLoader />;

  if (!user) {
    const from = `${location.pathname}${location.search}`;
    return <Navigate to="/login" state={{ from }} replace />;
  }

  if (user.must_change_password && location.pathname !== "/cambiar-clave") {
    return <Navigate to="/cambiar-clave" replace />;
  }

  return <>{children}</>;
}

/** Evita mostrar el login a quien ya tiene sesion iniciada. */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { user, isBootstrapping } = useAuth();

  if (isBootstrapping) return <FullPageLoader />;
  if (user) return <Navigate to={homePathFor(user.capabilities)} replace />;

  return <>{children}</>;
}

/** Restringe una ruta a los roles que pueden usarla. */
export function RequireCapability({
  allowed,
  children,
}: {
  allowed: (capabilities: Capabilities) => boolean;
  children: ReactNode;
}) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (!allowed(user.capabilities)) return <Navigate to={homePathFor(user.capabilities)} replace />;

  return <>{children}</>;
}

/** Redirige "/" al inicio que corresponde al rol. */
export function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homePathFor(user.capabilities)} replace />;
}
