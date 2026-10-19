import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/api/endpoints/auth";
import { AuthContext } from "./context";

/**
 * Estado de la sesion.
 *
 * No se guarda el usuario en `localStorage` ni el token en JavaScript: la
 * sesion vive en una cookie HttpOnly que el navegador envia sola. Aqui solo se
 * refleja en memoria lo que el servidor respondio en `/auth/me/`.
 */
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const refresh = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      // Sin sesion valida la API responde 401/403: no es un error a mostrar.
      setUser(null);
    }
  }, []);
  useEffect(() => {
    let cancelled = false;
    authApi
      .me()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setIsBootstrapping(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const login = useCallback(async (username, password) => {
    await authApi.login({
      username,
      password,
    });
    const me = await authApi.me();
    setUser(me);
  }, []);
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      // Los datos del usuario anterior no deben quedar en cache.
      queryClient.clear();
    }
  }, [queryClient]);
  const value = useMemo(
    () => ({
      user,
      isBootstrapping,
      isAuthenticated: user !== null,
      login,
      logout,
      refresh,
    }),
    [user, isBootstrapping, login, logout, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
