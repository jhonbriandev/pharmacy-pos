import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { AuthProvider } from "./AuthProvider";
import { LoginPage } from "./LoginPage";
const USER = {
  id: 3,
  username: "10000003",
  first_name: "Rosa",
  last_name: "Quispe",
  full_name: "Rosa Quispe",
  email: "",
  role: "CAJERO",
  role_display: "Cajero / Vendedor",
  is_active: true,
  must_change_password: false,
  last_login: null,
};
const ME = {
  ...USER,
  capabilities: {
    can_sell: true,
    can_manage_inventory: false,
    can_manage_catalog: false,
    can_manage_users: false,
    can_view_dashboard: false,
    can_view_all_sales: false,
    can_read_audit: false,
  },
};
function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div>Inicio del sistema</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

/** La primera consulta de sesion no encuentra cookie; a partir del login si. */
function mockSession(startAuthenticated = false) {
  let meCalls = startAuthenticated ? 1 : 0;
  server.use(
    http.get("/api/v1/auth/me/", () => {
      meCalls += 1;
      if (meCalls === 1) {
        return HttpResponse.json(
          {
            error: {
              code: "not_authenticated",
              message: "Debes iniciar sesion.",
            },
          },
          {
            status: 403,
          },
        );
      }
      return HttpResponse.json(ME);
    }),
  );
}
describe("LoginPage", () => {
  beforeEach(() => {
    mockSession();
  });
  it("exige un DNI de ocho digitos antes de llamar al servidor", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText(/DNI/i), "123");
    await user.click(
      screen.getByRole("button", {
        name: "Entrar",
      }),
    );
    expect(screen.getByText("El usuario es tu DNI: 8 digitos, sin espacios.")).toBeInTheDocument();
  });
  it("no permite un DNI de ocho digitos con contrasena vacia", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText(/DNI/i), "10000003");
    await user.click(
      screen.getByRole("button", {
        name: "Entrar",
      }),
    );
    expect(screen.getByText("Ingresa tu contrasena.")).toBeInTheDocument();
  });
  it("inicia sesion, envia el token CSRF y entra al sistema", async () => {
    const user = userEvent.setup();
    let loginBody = null;
    let csrfHeader = null;
    server.use(
      http.post("/api/v1/auth/login/", async ({ request }) => {
        loginBody = await request.json();
        csrfHeader = request.headers.get("x-csrftoken");
        return HttpResponse.json(USER);
      }),
    );
    renderLogin();
    await user.type(screen.getByLabelText(/DNI/i), "10000003");
    await user.type(screen.getByLabelText(/Contrasena/i), "Farmacia2026");
    await user.click(
      screen.getByRole("button", {
        name: "Entrar",
      }),
    );
    expect(await screen.findByText("Inicio del sistema")).toBeInTheDocument();
    expect(loginBody).toEqual({
      username: "10000003",
      password: "Farmacia2026",
    });
    expect(csrfHeader).toBe("test-token");
  });
  it("muestra el mensaje del servidor cuando las credenciales fallan", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/auth/login/", () =>
        HttpResponse.json(
          {
            error: {
              code: "authentication_failed",
              message: "Usuario o contrasena incorrectos.",
              details: null,
            },
          },
          {
            status: 401,
          },
        ),
      ),
    );
    renderLogin();
    await user.type(screen.getByLabelText(/DNI/i), "10000003");
    await user.type(screen.getByLabelText(/Contrasena/i), "incorrecta");
    await user.click(
      screen.getByRole("button", {
        name: "Entrar",
      }),
    );
    expect(await screen.findByText("Usuario o contrasena incorrectos.")).toBeInTheDocument();
    expect(screen.queryByText("Inicio del sistema")).not.toBeInTheDocument();
  });
  it("no muestra el campo de contrasena en texto plano", () => {
    renderLogin();
    expect(screen.getByLabelText(/Contrasena/i)).toHaveAttribute("type", "password");
  });
});
