import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Download, PackageX, TrendingDown } from "lucide-react";
import { errorMessage } from "@/api/client";
import { reportsApi } from "@/api/endpoints/reports";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card, PageHeader, StatCard } from "@/components/Card";
import { Field, Input } from "@/components/Field";
import { EmptyState, ErrorState, Spinner } from "@/components/Feedback";
import {
  formatDate,
  formatInteger,
  formatMoney,
  formatPercent,
  startOfMonthIso,
  todayIso,
} from "@/lib/format";
export function DashboardPage() {
  const [dateFrom, setDateFrom] = useState(startOfMonthIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const dashboardQuery = useQuery({
    queryKey: [
      "dashboard",
      {
        dateFrom,
        dateTo,
      },
    ],
    queryFn: () =>
      reportsApi.dashboard({
        date_from: dateFrom,
        date_to: dateTo,
      }),
  });
  const data = dashboardQuery.data;
  const maxDay = Math.max(1, ...(data?.sales_by_day.map((day) => Number(day.total)) ?? [1]));
  const paymentTotal = Math.max(
    1,
    ...(data?.sales_by_payment_method.map((row) => Number(row.total)) ?? [1]),
  );
  return (
    <div className="space-y-4">
      <PageHeader
        title="Dashboard"
        description="Indicadores del negocio, stock critico y vencimientos proximos."
        actions={
          <Button
            variant="secondary"
            onClick={() =>
              window.open(
                reportsApi.salesCsvUrl({
                  date_from: dateFrom,
                  date_to: dateTo,
                }),
                "_blank",
              )
            }
            icon={<Download className="size-4" aria-hidden />}
          >
            Exportar ventas
          </Button>
        }
      />

      <Card>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Desde" htmlFor="dash-from">
            <Input
              id="dash-from"
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </Field>
          <Field label="Hasta" htmlFor="dash-to">
            <Input
              id="dash-to"
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </Field>
          <div className="flex items-end lg:col-span-2">
            <p className="text-xs text-slate-500">
              Las fechas se interpretan en hora de Lima. El rango incluye las ventas del ultimo dia
              hasta las 23:59.
            </p>
          </div>
        </div>
      </Card>

      {dashboardQuery.isLoading ? (
        <Spinner label="Calculando indicadores" />
      ) : dashboardQuery.isError ? (
        <ErrorState
          message={errorMessage(dashboardQuery.error)}
          onRetry={() => void dashboardQuery.refetch()}
        />
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Ventas del periodo"
              value={formatMoney(data.summary.sales_total)}
              hint={`${formatInteger(data.summary.sales_count)} venta(s)`}
            />
            <StatCard
              label="Ticket promedio"
              value={formatMoney(data.summary.average_ticket)}
              hint={`Del ${formatDate(data.period.date_from)} al ${formatDate(data.period.date_to)}`}
            />
            <StatCard
              label="Margen bruto"
              value={formatMoney(data.gross_margin.margin)}
              hint={`${formatPercent(data.gross_margin.margin_percentage)} sobre ventas`}
              tone={Number(data.gross_margin.margin) >= 0 ? "positive" : "danger"}
            />
            <StatCard
              label="Inventario valorizado"
              value={formatMoney(data.inventory.cost_value)}
              hint={`${formatInteger(data.inventory.units)} unidades en stock`}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Ventas por dia" description="Solo se muestran los dias con ventas.">
              {data.sales_by_day.length === 0 ? (
                <EmptyState title="Sin ventas en el periodo" />
              ) : (
                <div>
                  <div className="flex h-44 items-end gap-1.5">
                    {data.sales_by_day.map((day) => (
                      <div
                        key={day.date}
                        className="group flex flex-1 flex-col items-center justify-end"
                      >
                        <span className="mb-1 hidden text-[10px] font-medium tabular-nums group-hover:block">
                          {formatMoney(day.total)}
                        </span>
                        <div
                          className="w-full rounded-t bg-brand-600 transition-colors group-hover:bg-brand-700"
                          style={{
                            height: `${Math.max(2, (Number(day.total) / maxDay) * 100)}%`,
                          }}
                          title={`${formatDate(day.date)}: ${formatMoney(day.total)} (${day.count} ventas)`}
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-2 flex justify-between text-xs text-slate-500">
                    <span>{formatDate(data.sales_by_day[0].date)}</span>
                    <span>{formatDate(data.sales_by_day[data.sales_by_day.length - 1].date)}</span>
                  </div>
                </div>
              )}
            </Card>

            <Card title="Medios de pago" description="Distribucion del monto cobrado.">
              {data.sales_by_payment_method.length === 0 ? (
                <EmptyState title="Sin cobros registrados" />
              ) : (
                <ul className="space-y-3">
                  {data.sales_by_payment_method.map((row) => (
                    <li key={row.method}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-slate-700">{row.label}</span>
                        <span className="tabular-nums">
                          {formatMoney(row.total)}{" "}
                          <span className="text-xs text-slate-500">({row.count})</span>
                        </span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-brand-600"
                          style={{
                            width: `${(Number(row.total) / paymentTotal) * 100}%`,
                          }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card
              title="Productos mas vendidos"
              description="Por cantidad de unidades."
              padded={false}
            >
              {data.top_products.length === 0 ? (
                <div className="p-4">
                  <EmptyState title="Sin ventas en el periodo" />
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.top_products.map((product, index) => (
                    <li key={product.product_id} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="w-5 text-sm font-semibold text-slate-400">{index + 1}</span>
                      <span className="min-w-0 flex-1 truncate text-sm text-slate-800">
                        {product.product_name}
                      </span>
                      <span className="text-sm font-medium tabular-nums">
                        {formatInteger(product.quantity)} u.
                      </span>
                      <span className="w-24 text-right text-sm tabular-nums text-slate-500">
                        {formatMoney(product.total)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card
              title={
                <span className="flex items-center gap-2">
                  <TrendingDown className="size-4 text-amber-600" aria-hidden /> Reposicion sugerida
                </span>
              }
              description="Productos activos por debajo del stock minimo."
              padded={false}
            >
              {data.low_stock.length === 0 ? (
                <div className="p-4">
                  <EmptyState
                    title="Stock saludable"
                    description="Ningun producto esta bajo su minimo."
                  />
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.low_stock.map((alert) => (
                    <li key={alert.product_id} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="min-w-0 flex-1 truncate text-sm text-slate-800">
                        {alert.product_name}
                      </span>
                      <Badge tone="warning">
                        {formatInteger(alert.stock)} / {formatInteger(alert.min_stock)}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card
              title={
                <span className="flex items-center gap-2">
                  <CalendarClock className="size-4 text-amber-600" aria-hidden /> Vencen pronto
                </span>
              }
              description="Lotes con existencias que vencen en los proximos 90 dias."
              padded={false}
            >
              {data.expiring_lots.length === 0 ? (
                <div className="p-4">
                  <EmptyState title="Nada por vencer" />
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.expiring_lots.map((lot) => (
                    <li key={lot.lot_id} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-slate-800">
                          {lot.product_name}
                        </span>
                        <span className="block text-xs text-slate-500">
                          Lote {lot.batch_number} · {formatDate(lot.expiry_date)}
                        </span>
                      </span>
                      <Badge tone={lot.days_left <= 30 ? "danger" : "warning"}>
                        {lot.days_left} dias
                      </Badge>
                      <span className="text-sm tabular-nums text-slate-600">
                        {formatInteger(lot.quantity)} u.
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card
              title={
                <span className="flex items-center gap-2">
                  <PackageX className="size-4 text-red-600" aria-hidden /> Vencidos con stock
                </span>
              }
              description="Hay que darlos de baja para que no se vendan."
              padded={false}
            >
              {data.expired_lots.length === 0 ? (
                <div className="p-4">
                  <EmptyState
                    title="Sin pendientes"
                    description="No hay lotes vencidos con existencias."
                  />
                </div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {data.expired_lots.map((lot) => (
                    <li key={lot.lot_id} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-slate-800">
                          {lot.product_name}
                        </span>
                        <span className="block text-xs text-slate-500">
                          Lote {lot.batch_number} · {formatDate(lot.expiry_date)}
                        </span>
                      </span>
                      <Badge tone="danger">Hace {lot.days_overdue} dias</Badge>
                      <span className="text-sm tabular-nums text-slate-600">
                        {formatInteger(lot.quantity)} u.
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
