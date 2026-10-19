import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./AppLayout";
import { HomeRedirect, ProtectedRoute, RedirectIfAuthenticated, RequireCapability } from "./guards";
import { NotFoundPage } from "./NotFoundPage";
import { AuditPage } from "@/features/audit/AuditPage";
import { ChangePasswordPage } from "@/features/auth/ChangePasswordPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { CatalogPage } from "@/features/catalog/CatalogPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { InventoryPage } from "@/features/inventory/InventoryPage";
import { PosPage } from "@/features/pos/PosPage";
import { SalesHistoryPage } from "@/features/sales/SalesHistoryPage";
import { UsersPage } from "@/features/users/UsersPage";

/**
 * Rutas de la aplicacion.
 *
 * Los permisos se verifican dos veces: aqui para no mostrar pantallas que el
 * rol no puede usar, y en el backend, que es la unica verificacion que cuenta.
 */
export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <RedirectIfAuthenticated>
        <LoginPage />
      </RedirectIfAuthenticated>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <HomeRedirect />,
      },
      {
        path: "pos",
        element: (
          <RequireCapability allowed={(capabilities) => capabilities.can_sell}>
            <PosPage />
          </RequireCapability>
        ),
      },
      {
        path: "ventas",
        element: <SalesHistoryPage />,
      },
      {
        path: "inventario",
        element: <InventoryPage />,
      },
      {
        path: "catalogo",
        element: <CatalogPage />,
      },
      {
        path: "dashboard",
        element: (
          <RequireCapability allowed={(capabilities) => capabilities.can_view_dashboard}>
            <DashboardPage />
          </RequireCapability>
        ),
      },
      {
        path: "usuarios",
        element: (
          <RequireCapability allowed={(capabilities) => capabilities.can_manage_users}>
            <UsersPage />
          </RequireCapability>
        ),
      },
      {
        path: "auditoria",
        element: (
          <RequireCapability allowed={(capabilities) => capabilities.can_read_audit}>
            <AuditPage />
          </RequireCapability>
        ),
      },
      {
        path: "cambiar-clave",
        element: <ChangePasswordPage />,
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
]);
