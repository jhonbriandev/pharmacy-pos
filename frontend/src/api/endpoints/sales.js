/** Endpoints de ventas y boletas. */

import { apiRequest } from "../client";
export const salesApi = {
  /**
   * Registra la venta.
   *
   * El identificador de la peticion hace la operacion idempotente: si la red
   * falla y el usuario reintenta, el servidor devuelve la venta ya creada en
   * lugar de cobrar dos veces.
   */
  create: (payload) =>
    apiRequest("/sales/", {
      method: "POST",
      body: payload,
    }),
  list: (params = {}) =>
    apiRequest("/sales/", {
      query: {
        status: params.status,
        date_from: params.date_from,
        date_to: params.date_to,
        search: params.search,
        page: params.page,
      },
    }),
  get: (id) => apiRequest(`/sales/${id}/`),
  receipt: (number) => apiRequest(`/receipts/${number}/`),
};
