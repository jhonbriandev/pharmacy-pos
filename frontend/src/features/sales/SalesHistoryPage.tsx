import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Printer, ReceiptText, Search } from "lucide-react";

import { errorMessage } from "@/api/client";
import { salesApi } from "@/api/endpoints/sales";
import type { Sale } from "@/api/types";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card, PageHeader } from "@/components/Card";
import { Field, Input } from "@/components/Field";
import { Alert, EmptyState, ErrorState, Spinner } from "@/components/Feedback";
import { Modal } from "@/components/Modal";
import { Pagination, Table, TBody, TD, TH, THead, TR, TableMessage } from "@/components/Table";
import { formatDateTime, formatMoney, startOfMonthIso, todayIso } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";
import { useAuth } from "@/features/auth/context";
import { ReceiptTicket } from "./ReceiptTicket";

const PAGE_SIZE = 25;

function statusTone(status: Sale["status"]) {
  return status === "CONFIRMADA" ? "success" : "danger";
}

export function SalesHistoryPage() {
  const { user } = useAuth();
  const canSeeAll = user?.capabilities.can_view_all_sales ?? false;

  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState(startOfMonthIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim(), 300);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [receiptNumber, setReceiptNumber] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, dateFrom, dateTo]);

  const salesQuery = useQuery({
    queryKey: ["sales", { page, dateFrom, dateTo, search: debouncedSearch }],
    queryFn: () =>
      salesApi.list({
        page,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: debouncedSearch || undefined,
      }),
  });

  const detailQuery = useQuery({
    queryKey: ["sale", selectedId],
    queryFn: () => salesApi.get(selectedId as number),
    enabled: selectedId !== null,
  });

  const receiptQuery = useQuery({
    queryKey: ["receipt", receiptNumber],
    queryFn: () => salesApi.receipt(receiptNumber as string),
    enabled: receiptNumber !== null,
    staleTime: Infinity,
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Ventas"
        description={
          canSeeAll
            ? "Historial de todas las ventas del equipo."
            : "Aqui aparecen unicamente las ventas que registraste."
        }
      />

      <Card padded={false}>
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Desde" htmlFor="sales-from">
            <Input
              id="sales-from"
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </Field>
          <Field label="Hasta" htmlFor="sales-to">
            <Input
              id="sales-to"
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </Field>
          <Field label="Numero de venta" htmlFor="sales-search" className="sm:col-span-2">
            <div className="relative">
              <Search
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <Input
                id="sales-search"
                placeholder="00000012"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="pl-9"
              />
            </div>
          </Field>
        </div>

        {salesQuery.isError ? (
          <div className="p-4">
            <ErrorState
              message={errorMessage(salesQuery.error)}
              onRetry={() => void salesQuery.refetch()}
            />
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <TH>Numero</TH>
                  <TH>Fecha y hora</TH>
                  {canSeeAll && <TH>Vendedor</TH>}
                  <TH className="text-right">Items</TH>
                  <TH className="text-right">Total</TH>
                  <TH>Estado</TH>
                  <TH className="text-right">Acciones</TH>
                </tr>
              </THead>
              <TBody>
                {salesQuery.isLoading ? (
                  <TableMessage colSpan={canSeeAll ? 7 : 6}>
                    <Spinner label="Cargando ventas" />
                  </TableMessage>
                ) : salesQuery.data && salesQuery.data.results.length > 0 ? (
                  salesQuery.data.results.map((sale) => (
                    <TR key={sale.id} onClick={() => setSelectedId(sale.id)}>
                      <TD className="font-mono font-medium text-slate-900">{sale.number}</TD>
                      <TD>{formatDateTime(sale.created_at)}</TD>
                      {canSeeAll && <TD>{sale.seller_name}</TD>}
                      <TD className="text-right tabular-nums">{sale.items.length}</TD>
                      <TD className="text-right font-semibold tabular-nums">
                        {formatMoney(sale.total)}
                      </TD>
                      <TD>
                        <Badge tone={statusTone(sale.status)}>{sale.status_display}</Badge>
                      </TD>
                      <TD className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(event) => {
                            event.stopPropagation();
                            setReceiptNumber(sale.number);
                          }}
                          icon={<ReceiptText className="size-4" aria-hidden />}
                        >
                          Boleta
                        </Button>
                      </TD>
                    </TR>
                  ))
                ) : (
                  <TableMessage colSpan={canSeeAll ? 7 : 6}>
                    <EmptyState
                      title="Sin ventas en el periodo"
                      description="Prueba con otro rango de fechas."
                    />
                  </TableMessage>
                )}
              </TBody>
            </Table>

            {salesQuery.data && (
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                count={salesQuery.data.count}
                onChange={setPage}
              />
            )}
          </>
        )}
      </Card>

      <Modal
        open={selectedId !== null}
        onClose={() => setSelectedId(null)}
        title={detailQuery.data ? `Venta ${detailQuery.data.number}` : "Detalle de venta"}
        description="Detalle interno: incluye costo y margen de cada linea."
        size="lg"
        footer={
          detailQuery.data && (
            <Button
              variant="secondary"
              onClick={() => setReceiptNumber(detailQuery.data.number)}
              icon={<Printer className="size-4" aria-hidden />}
            >
              Ver boleta
            </Button>
          )
        }
      >
        {detailQuery.isLoading ? (
          <Spinner />
        ) : detailQuery.isError ? (
          <Alert tone="danger">{errorMessage(detailQuery.error)}</Alert>
        ) : detailQuery.data ? (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-slate-500">Vendedor</dt>
                <dd className="font-medium">{detailQuery.data.seller_name}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Fecha</dt>
                <dd className="font-medium">{formatDateTime(detailQuery.data.created_at)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Estado</dt>
                <dd>
                  <Badge tone={statusTone(detailQuery.data.status)}>
                    {detailQuery.data.status_display}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Total</dt>
                <dd className="font-semibold tabular-nums">{formatMoney(detailQuery.data.total)}</dd>
              </div>
            </dl>

            <div className="overflow-hidden rounded-lg border border-slate-200">
              <Table>
                <THead>
                  <tr>
                    <TH>Producto</TH>
                    <TH className="text-right">Cant.</TH>
                    <TH className="text-right">Precio</TH>
                    <TH className="text-right">Costo</TH>
                    <TH className="text-right">Margen</TH>
                    <TH>Lotes usados</TH>
                  </tr>
                </THead>
                <TBody>
                  {detailQuery.data.items.map((item) => (
                    <TR key={item.id}>
                      <TD>{item.product_name}</TD>
                      <TD className="text-right tabular-nums">{item.quantity}</TD>
                      <TD className="text-right tabular-nums">{formatMoney(item.unit_price)}</TD>
                      <TD className="text-right tabular-nums text-slate-500">
                        {formatMoney(item.unit_cost)}
                      </TD>
                      <TD className="text-right font-medium tabular-nums text-brand-700">
                        {formatMoney(item.margin)}
                      </TD>
                      <TD className="text-xs text-slate-500">
                        {item.lot_allocations
                          .map((lot) => `${lot.batch_number} (${lot.quantity})`)
                          .join(", ")}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>

            {detailQuery.data.payments.length > 0 && (
              <p className="text-sm text-slate-600">
                Pago: {detailQuery.data.payments.map((payment) => payment.method_display).join(", ")}
                {detailQuery.data.payments[0].received_amount && (
                  <>
                    {" "}
                    · recibido {formatMoney(detailQuery.data.payments[0].received_amount)} · vuelto{" "}
                    {formatMoney(detailQuery.data.payments[0].change_amount)}
                  </>
                )}
              </p>
            )}
          </div>
        ) : null}
      </Modal>

      <Modal
        open={receiptNumber !== null}
        onClose={() => setReceiptNumber(null)}
        title={`Boleta ${receiptNumber ?? ""}`}
        size="sm"
        footer={
          <Button onClick={() => window.print()} icon={<Printer className="size-4" aria-hidden />}>
            Imprimir
          </Button>
        }
      >
        {receiptQuery.isLoading ? (
          <Spinner />
        ) : receiptQuery.data ? (
          <ReceiptTicket receipt={receiptQuery.data} />
        ) : (
          <Alert tone="danger">{errorMessage(receiptQuery.error)}</Alert>
        )}
      </Modal>
    </div>
  );
}
