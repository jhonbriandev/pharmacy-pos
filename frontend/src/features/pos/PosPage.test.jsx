import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/server";
import { AuthContext } from "@/features/auth/context";
import { PosPage } from "./PosPage";
const CASHIER = {
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
const PRODUCT = {
  id: 1,
  display_name: "Paracetamol 500 mg - Caja x 100",
  barcode: "7751234500011",
  presentation: "CAJA",
  presentation_display: "Caja",
  sale_price: "12.00",
  tax_rate: "18.00",
  last_cost: "8.0000",
  stock: 10,
  lots: [
    {
      id: 1,
      batch_number: "LOTE-1",
      expiry_date: "2027-01-27",
      quantity: 10,
    },
  ],
};
const SALE = {
  id: 42,
  number: "00000042",
  status: "CONFIRMADA",
  status_display: "Confirmada",
  total: "12.00",
  seller_name: "Rosa Quispe",
  created_at: "2026-10-19T10:15:00-05:00",
  notes: "",
  created_by: 3,
  items: [
    {
      id: 1,
      product: 1,
      product_name: PRODUCT.display_name,
      quantity: 1,
      unit_price: "12.00",
      line_total: "12.00",
      unit_cost: "8.0000",
      margin: "4.00",
      lot_allocations: [
        {
          id: 1,
          lot: 1,
          batch_number: "LOTE-1",
          expiry_date: "2027-01-27",
          quantity: 1,
          unit_cost: "8.0000",
        },
      ],
    },
  ],
  payments: [
    {
      id: 1,
      method: "EFECTIVO",
      method_display: "Efectivo",
      amount: "12.00",
      received_amount: "12.00",
      change_amount: "0.00",
      reference: "",
    },
  ],
};
const RECEIPT = {
  number: "00000042",
  created_at: "2026-10-19T10:15:00-05:00",
  seller_name: "Rosa Quispe",
  items: [
    {
      product_name: PRODUCT.display_name,
      quantity: 1,
      unit_price: "12.00",
      line_total: "12.00",
    },
  ],
  total: "12.00",
  payment: {
    method: "Efectivo",
    amount: "12.00",
    received_amount: "12.00",
    change_amount: "0.00",
    reference: "",
  },
};
function renderPos() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider
        value={{
          user: CASHIER,
          isBootstrapping: false,
          isAuthenticated: true,
          login: async () => undefined,
          logout: async () => undefined,
          refresh: async () => undefined,
        }}
      >
        <PosPage />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}
describe("PosPage", () => {
  let saleBody;
  beforeEach(() => {
    saleBody = null;
    server.use(
      http.get("/api/v1/products/lookup/", () => HttpResponse.json([PRODUCT])),
      http.post("/api/v1/sales/", async ({ request }) => {
        saleBody = await request.json();
        return HttpResponse.json(SALE, {
          status: 201,
        });
      }),
      http.get("/api/v1/receipts/:number/", () => HttpResponse.json(RECEIPT)),
    );
  });
  it("busca, agrega al carrito y cobra con vuelto calculado en pantalla", async () => {
    const user = userEvent.setup();
    renderPos();
    await user.type(screen.getByLabelText("Buscar producto"), "paracetamol");
    const result = await screen.findByRole("button", {
      name: /Paracetamol 500 mg/,
    });
    await user.click(result);

    // El carrito muestra el producto y el total del servidor (12.00).
    expect(screen.getByLabelText("Cantidad de Paracetamol 500 mg - Caja x 100")).toHaveValue(1);
    expect(
      screen.getByRole("button", {
        name: /Cobrar/,
      }),
    ).toHaveTextContent("12.00");
    await user.click(
      screen.getByRole("button", {
        name: "Exacto",
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: /Cobrar/,
      }),
    );
    expect(await screen.findByText("Venta registrada")).toBeInTheDocument();
    expect(screen.getAllByText(/00000042/).length).toBeGreaterThan(0);
    expect(saleBody).not.toBeNull();
    expect(saleBody?.items).toEqual([
      {
        product_id: 1,
        quantity: 1,
      },
    ]);
    expect(saleBody?.payment).toMatchObject({
      method: "EFECTIVO",
      received_amount: "12.00",
    });
    expect(String(saleBody?.client_request_id)).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });
  it("no deja cobrar con el carrito vacio", () => {
    renderPos();
    expect(
      screen.getByRole("button", {
        name: /Cobrar/,
      }),
    ).toBeDisabled();
  });
  it("no permite agregar un producto sin stock vendible", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/v1/products/lookup/", () =>
        HttpResponse.json([
          {
            ...PRODUCT,
            id: 2,
            display_name: "Ibuprofeno 400 mg",
            stock: 0,
          },
        ]),
      ),
    );
    renderPos();
    await user.type(screen.getByLabelText("Buscar producto"), "ibuprofeno");
    const result = await screen.findByRole("button", {
      name: /Ibuprofeno 400 mg/,
    });
    expect(result).toBeDisabled();
    expect(within(result).getByText("Sin stock")).toBeInTheDocument();
  });
  it("muestra el error del backend y no abre la boleta si falta stock", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/v1/sales/", () =>
        HttpResponse.json(
          {
            error: {
              code: "insufficient_stock",
              message: "No hay stock suficiente para completar la operacion.",
              details: {
                requested: 1,
              },
            },
          },
          {
            status: 409,
          },
        ),
      ),
    );
    renderPos();
    await user.type(screen.getByLabelText("Buscar producto"), "paracetamol");
    await user.click(
      await screen.findByRole("button", {
        name: /Paracetamol 500 mg/,
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: "Exacto",
      }),
    );
    await user.click(
      screen.getByRole("button", {
        name: /Cobrar/,
      }),
    );
    expect(
      await screen.findByText("No hay stock suficiente para completar la operacion."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Venta registrada")).not.toBeInTheDocument();
    // El carrito se conserva para que el cajero pueda corregir.
    expect(
      screen.getByRole("button", {
        name: /Cobrar/,
      }),
    ).toHaveTextContent("12.00");
  });
});
