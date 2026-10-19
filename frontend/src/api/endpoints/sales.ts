/** Endpoints de ventas y boletas. */

import { apiRequest } from "../client";
import type { Paginated, PaymentMethod, Receipt, Sale, SaleStatus } from "../types";

export interface SaleItemPayload {
  product_id: number;
  quantity: number;
}

export interface SalePaymentPayload {
  method: PaymentMethod;
  received_amount?: string | null;
  reference?: string;
}

export interface SaleCreatePayload {
  client_request_id: string;
  items: SaleItemPayload[];
  payment: SalePaymentPayload;
  notes?: string;
}

export interface SaleListParams {
  status?: SaleStatus;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
}

export const salesApi = {
  /**
   * Registra la venta.
   *
   * El identificador de la peticion hace la operacion idempotente: si la red
   * falla y el usuario reintenta, el servidor devuelve la venta ya creada en
   * lugar de cobrar dos veces.
   */
  create: (payload: SaleCreatePayload) =>
    apiRequest<Sale>("/sales/", { method: "POST", body: payload }),

  list: (params: SaleListParams = {}) =>
    apiRequest<Paginated<Sale>>("/sales/", {
      query: {
        status: params.status,
        date_from: params.date_from,
        date_to: params.date_to,
        search: params.search,
        page: params.page,
      },
    }),

  get: (id: number) => apiRequest<Sale>(`/sales/${id}/`),

  receipt: (number: string) => apiRequest<Receipt>(`/receipts/${number}/`),
};
