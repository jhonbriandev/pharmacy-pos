import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import { AuthProvider } from "@/features/auth/AuthProvider";

/**
 * Cliente de datos.
 *
 * Los errores 4xx no se reintentan: si el backend dijo "sin permisos" o "sin
 * stock", repetir la peticion solo multiplica el error. Los fallos de red o de
 * servidor se reintentan dos veces con espera creciente.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 5000),
    },
    mutations: {
      retry: false,
    },
  },
});
export function AppProviders({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
