import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { errorMessage } from "@/api/client";
import { auditApi } from "@/api/endpoints/reports";
import { Badge } from "@/components/Badge";
import { Card, PageHeader } from "@/components/Card";
import { Field, Input, Select } from "@/components/Field";
import { EmptyState, ErrorState, Spinner } from "@/components/Feedback";
import { Pagination, Table, TBody, TD, TH, THead, TR, TableMessage } from "@/components/Table";
import { formatDateTime, startOfMonthIso, todayIso } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";
const PAGE_SIZE = 25;

/** Acciones registradas por el backend (apps/audit/models.py). */
const ACTIONS = [
  {
    value: "LOGIN_OK",
    label: "Inicio de sesion",
  },
  {
    value: "LOGIN_FAIL",
    label: "Intento fallido",
  },
  {
    value: "LOGOUT",
    label: "Cierre de sesion",
  },
  {
    value: "PASSWORD_CHANGED",
    label: "Cambio de contrasena",
  },
  {
    value: "PASSWORD_RESET",
    label: "Restablecimiento de contrasena",
  },
  {
    value: "USER_CREATED",
    label: "Usuario creado",
  },
  {
    value: "USER_UPDATED",
    label: "Usuario actualizado",
  },
  {
    value: "USER_DEACTIVATED",
    label: "Usuario desactivado",
  },
  {
    value: "ROLE_CHANGED",
    label: "Cambio de rol",
  },
  {
    value: "PRODUCT_CREATED",
    label: "Producto creado",
  },
  {
    value: "PRODUCT_UPDATED",
    label: "Producto actualizado",
  },
  {
    value: "PRICE_CHANGED",
    label: "Cambio de precio",
  },
  {
    value: "STOCK_ENTRY_CREATED",
    label: "Entrada de mercaderia",
  },
  {
    value: "STOCK_ADJUSTMENT",
    label: "Ajuste de stock",
  },
  {
    value: "LOT_BLOCKED",
    label: "Lote bloqueado",
  },
  {
    value: "SALE_CREATED",
    label: "Venta registrada",
  },
];
function actionTone(action) {
  if (action.startsWith("LOGIN_FAIL")) return "danger";
  if (action.startsWith("USER_") || action.startsWith("ROLE_")) return "warning";
  if (action.startsWith("STOCK_") || action.startsWith("SALE_")) return "info";
  return "neutral";
}
function summarize(event) {
  const payload = event.after ?? event.before;
  if (!payload) return "—";
  return Object.entries(payload)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join(" · ");
}
export function AuditPage() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState(startOfMonthIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  useEffect(() => {
    setPage(1);
  }, [action, debouncedSearch, dateFrom, dateTo]);
  const auditQuery = useQuery({
    queryKey: [
      "audit",
      {
        page,
        action,
        search: debouncedSearch,
        dateFrom,
        dateTo,
      },
    ],
    queryFn: () =>
      auditApi.list({
        page,
        action: action || undefined,
        search: debouncedSearch || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
  });
  return (
    <div className="space-y-4">
      <PageHeader
        title="Auditoria"
        description="Registro inmutable de las acciones sensibles. No se puede editar ni borrar."
      />

      <Card padded={false}>
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Desde" htmlFor="audit-from">
            <Input
              id="audit-from"
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </Field>
          <Field label="Hasta" htmlFor="audit-to">
            <Input
              id="audit-to"
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </Field>
          <Field label="Accion" htmlFor="audit-action">
            <Select
              id="audit-action"
              value={action}
              onChange={(event) => setAction(event.target.value)}
            >
              <option value="">Todas</option>
              {ACTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Buscar" htmlFor="audit-search">
            <div className="relative">
              <Search
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <Input
                id="audit-search"
                placeholder="Usuario o entidad…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="pl-9"
              />
            </div>
          </Field>
        </div>

        {auditQuery.isError ? (
          <div className="p-4">
            <ErrorState
              message={errorMessage(auditQuery.error)}
              onRetry={() => void auditQuery.refetch()}
            />
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <TH>Fecha y hora</TH>
                  <TH>Accion</TH>
                  <TH>Usuario</TH>
                  <TH>Entidad</TH>
                  <TH>Detalle</TH>
                  <TH>IP</TH>
                </tr>
              </THead>
              <TBody>
                {auditQuery.isLoading ? (
                  <TableMessage colSpan={6}>
                    <Spinner label="Cargando auditoria" />
                  </TableMessage>
                ) : auditQuery.data && auditQuery.data.results.length > 0 ? (
                  auditQuery.data.results.map((event) => (
                    <TR key={event.id}>
                      <TD className="whitespace-nowrap">{formatDateTime(event.created_at)}</TD>
                      <TD>
                        <Badge tone={actionTone(event.action)}>{event.action_display}</Badge>
                      </TD>
                      <TD>
                        <p className="font-medium text-slate-900">
                          {event.actor_name || "Sistema"}
                        </p>
                        {event.actor_username && (
                          <p className="font-mono text-xs text-slate-500">{event.actor_username}</p>
                        )}
                      </TD>
                      <TD className="font-mono text-xs text-slate-500">
                        {event.entity_type ? `${event.entity_type} #${event.entity_id}` : "—"}
                      </TD>
                      <TD className="max-w-md truncate text-slate-600" title={summarize(event)}>
                        {summarize(event)}
                      </TD>
                      <TD className="font-mono text-xs text-slate-500">
                        {event.ip_address ?? "—"}
                      </TD>
                    </TR>
                  ))
                ) : (
                  <TableMessage colSpan={6}>
                    <EmptyState
                      title="Sin eventos"
                      description="No hay acciones registradas en el periodo seleccionado."
                    />
                  </TableMessage>
                )}
              </TBody>
            </Table>
            {auditQuery.data && (
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                count={auditQuery.data.count}
                onChange={setPage}
              />
            )}
          </>
        )}
      </Card>
    </div>
  );
}
