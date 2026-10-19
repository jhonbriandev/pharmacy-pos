import { createContext, useContext } from "react";

import type { Me } from "@/api/types";

export interface AuthContextValue {
  user: Me | null;
  /** `true` mientras se consulta la sesion existente al arrancar. */
  isBootstrapping: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Vuelve a leer el usuario (por ejemplo tras cambiar la contrasena). */
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  }
  return context;
}
