/** Endpoints de reportes y auditoria. */

import { apiRequest } from "../client";
import type { AuditEvent, Dashboard, Paginated } from "../types";

export interface DateRangeParams {
  date_from?: string;
  date_to?: string;
}

export const reportsApi = {
  dashboard: (params: DateRangeParams = {}) =>
    apiRequest<Dashboard>("/reports/dashboard/", {
      query: { date_from: params.date_from, date_to: params.date_to },
    }),

  /** URL de descarga del CSV de ventas (la abre el navegador directamente). */
  salesCsvUrl: (params: DateRangeParams = {}) => {
    const base = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/+$/, "");
    const search = new URLSearchParams();
    if (params.date_from) search.set("date_from", params.date_from);
    if (params.date_to) search.set("date_to", params.date_to);
    const query = search.toString();
    return `${base}/reports/exports/sales.csv${query ? `?${query}` : ""}`;
  },
};

export const auditApi = {
  list: (params: { action?: string; search?: string; date_from?: string; date_to?: string; page?: number } = {}) =>
    apiRequest<Paginated<AuditEvent>>("/audit-events/", {
      query: {
        action: params.action,
        search: params.search,
        date_from: params.date_from,
        date_to: params.date_to,
        page: params.page,
      },
    }),
};
