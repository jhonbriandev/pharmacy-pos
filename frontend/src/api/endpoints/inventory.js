/** Endpoints de inventario: lotes, entradas, ajustes y fraccionamiento. */

import { apiRequest } from "../client";
export const inventoryApi = {
  lots: (params = {}) =>
    apiRequest("/lots/", {
      query: {
        search: params.search,
        product: params.product,
        is_blocked: params.is_blocked,
        page: params.page,
      },
    }),
  expiringLots: (withinDays = 90) =>
    apiRequest("/lots/expiring/", {
      query: {
        within_days: withinDays,
      },
    }),
  expiredLots: () => apiRequest("/lots/expired/"),
  blockLot: (lotId, reason) =>
    apiRequest(`/lots/${lotId}/block/`, {
      method: "POST",
      body: {
        reason,
      },
    }),
  entries: (params = {}) =>
    apiRequest("/stock-entries/", {
      query: {
        search: params.search,
        page: params.page,
      },
    }),
  entry: (id) => apiRequest(`/stock-entries/${id}/`),
  createEntry: (payload) =>
    apiRequest("/stock-entries/", {
      method: "POST",
      body: payload,
    }),
  movements: (params = {}) =>
    apiRequest("/stock-movements/", {
      query: {
        date_from: params.date_from,
        date_to: params.date_to,
        page: params.page,
      },
    }),
  adjust: (payload) =>
    apiRequest("/stock-adjustments/", {
      method: "POST",
      body: payload,
    }),
  fractionate: (payload) =>
    apiRequest("/stock-fractionations/", {
      method: "POST",
      body: payload,
    }),
  consistency: () => apiRequest("/inventory/consistency/"),
};
