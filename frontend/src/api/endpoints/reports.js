/** Endpoints de reportes y auditoria. */

import { apiRequest } from "../client";
export const reportsApi = {
  dashboard: (params = {}) =>
    apiRequest("/reports/dashboard/", {
      query: {
        date_from: params.date_from,
        date_to: params.date_to,
      },
    }),
  /** URL de descarga del CSV de ventas (la abre el navegador directamente). */
  salesCsvUrl: (params = {}) => {
    const base = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/+$/, "");
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    const query = search.toString();
    return `${base}/reports/exports/sales.csv${query ? `?${query}` : ""}`;
  },
};
export const auditApi = {
  list: (params = {}) =>
    apiRequest("/audit-events/", {
      query: {
        action: params.action,
        search: params.search,
        date_from: params.date_from,
        date_to: params.date_to,
        page: params.page,
      },
    }),
};
