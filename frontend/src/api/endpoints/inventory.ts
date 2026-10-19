/** Endpoints de inventario: lotes, entradas, ajustes y fraccionamiento. */

import { apiRequest } from "../client";
import type {
  ConsistencyReport,
  Lot,
  Paginated,
  StockEntry,
  StockMovement,
} from "../types";

export interface LotListParams {
  search?: string;
  product?: number;
  is_blocked?: boolean;
  page?: number;
}

export interface StockEntryItemPayload {
  product: number;
  batch_number: string;
  expiry_date: string;
  quantity: number;
  cost_price: string;
}

export interface StockEntryPayload {
  client_request_id: string;
  supplier: string;
  document_number?: string;
  received_at: string;
  notes?: string;
  items: StockEntryItemPayload[];
}

export interface AdjustmentPayload {
  lot: number;
  quantity_delta: number;
  reason: string;
  notes?: string;
  movement_type?: string;
}

export interface FractionationPayload {
  source_lot: number;
  quantity: number;
  batch_number: string;
  expiry_date: string;
  reason?: string;
}

export const inventoryApi = {
  lots: (params: LotListParams = {}) =>
    apiRequest<Paginated<Lot>>("/lots/", {
      query: {
        search: params.search,
        product: params.product,
        is_blocked: params.is_blocked,
        page: params.page,
      },
    }),

  expiringLots: (withinDays = 90) =>
    apiRequest<Lot[]>("/lots/expiring/", { query: { within_days: withinDays } }),

  expiredLots: () => apiRequest<Lot[]>("/lots/expired/"),

  blockLot: (lotId: number, reason: string) =>
    apiRequest<Lot>(`/lots/${lotId}/block/`, { method: "POST", body: { reason } }),

  entries: (params: { search?: string; page?: number } = {}) =>
    apiRequest<Paginated<StockEntry>>("/stock-entries/", {
      query: { search: params.search, page: params.page },
    }),

  entry: (id: number) => apiRequest<StockEntry>(`/stock-entries/${id}/`),

  createEntry: (payload: StockEntryPayload) =>
    apiRequest<StockEntry>("/stock-entries/", { method: "POST", body: payload }),

  movements: (params: { date_from?: string; date_to?: string; page?: number } = {}) =>
    apiRequest<Paginated<StockMovement>>("/stock-movements/", {
      query: { date_from: params.date_from, date_to: params.date_to, page: params.page },
    }),

  adjust: (payload: AdjustmentPayload) =>
    apiRequest<StockMovement>("/stock-adjustments/", { method: "POST", body: payload }),

  fractionate: (payload: FractionationPayload) =>
    apiRequest<{ out: StockMovement; in: StockMovement }>("/stock-fractionations/", {
      method: "POST",
      body: payload,
    }),

  consistency: () => apiRequest<ConsistencyReport>("/inventory/consistency/"),
};
