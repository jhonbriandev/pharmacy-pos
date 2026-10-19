import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarClock,
  PackagePlus,
  Search,
  SlidersHorizontal,
  Split,
  Ban,
} from "lucide-react";
import { errorMessage } from "@/api/client";
import { inventoryApi } from "@/api/endpoints/inventory";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card, PageHeader } from "@/components/Card";
import { Field, Input } from "@/components/Field";
import { Alert, EmptyState, ErrorState, Spinner } from "@/components/Feedback";
import { Pagination, Table, TBody, TD, TH, THead, TR, TableMessage } from "@/components/Table";
import { useAuth } from "@/features/auth/context";
import { cn } from "@/lib/cn";
import {
  describeExpiry,
  formatDate,
  formatDateTime,
  formatInteger,
  startOfMonthIso,
  todayIso,
} from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";
import { AdjustLotModal, BlockLotModal, FractionationModal } from "./LotActionModals";
import { StockEntryModal } from "./StockEntryModal";
const PAGE_SIZE = 25;
const TABS = [
  {
    id: "vencimientos",
    label: "Vencimientos",
  },
  {
    id: "lotes",
    label: "Lotes",
  },
  {
    id: "movimientos",
    label: "Movimientos",
  },
];
function ExpiryBadge({ lot }) {
  if (lot.is_blocked) return <Badge tone="warning">Bloqueado</Badge>;
  if (lot.is_expired) return <Badge tone="danger">Vencido</Badge>;
  const expiry = describeExpiry(lot.expiry_date);
  return <Badge tone={expiry.tone === "warning" ? "warning" : "success"}>{expiry.text}</Badge>;
}
function LotActions({ lot, canManage, onAdjust, onFractionate, onBlock }) {
  if (!canManage) return null;
  return (
    <div className="flex justify-end gap-1">
      <Button
        variant="ghost"
        size="sm"
        title="Ajustar stock"
        aria-label={`Ajustar stock del lote ${lot.batch_number}`}
        onClick={() => onAdjust(lot)}
        icon={<SlidersHorizontal className="size-4" aria-hidden />}
      />
      <Button
        variant="ghost"
        size="sm"
        title="Fraccionar"
        aria-label={`Fraccionar el lote ${lot.batch_number}`}
        onClick={() => onFractionate(lot)}
        icon={<Split className="size-4" aria-hidden />}
      />
      <Button
        variant="ghost"
        size="sm"
        title="Bloquear lote"
        aria-label={`Bloquear el lote ${lot.batch_number}`}
        onClick={() => onBlock(lot)}
        icon={<Ban className="size-4" aria-hidden />}
      />
    </div>
  );
}
export function InventoryPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canManage = user?.capabilities.can_manage_inventory ?? false;
  const [tab, setTab] = useState("vencimientos");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  const [movementFrom, setMovementFrom] = useState(startOfMonthIso());
  const [movementTo, setMovementTo] = useState(todayIso());
  const [movementPage, setMovementPage] = useState(1);
  const [entryOpen, setEntryOpen] = useState(false);
  const [adjustLot, setAdjustLot] = useState(null);
  const [fractionLot, setFractionLot] = useState(null);
  const [blockLot, setBlockLot] = useState(null);
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);
  const expiringQuery = useQuery({
    queryKey: ["lots", "expiring"],
    queryFn: () => inventoryApi.expiringLots(90),
  });
  const expiredQuery = useQuery({
    queryKey: ["lots", "expired"],
    queryFn: () => inventoryApi.expiredLots(),
  });
  const lotsQuery = useQuery({
    queryKey: [
      "lots",
      "list",
      {
        page,
        search: debouncedSearch,
      },
    ],
    queryFn: () =>
      inventoryApi.lots({
        page,
        search: debouncedSearch || undefined,
      }),
    enabled: tab === "lotes",
  });
  const movementsQuery = useQuery({
    queryKey: [
      "movements",
      {
        page: movementPage,
        from: movementFrom,
        to: movementTo,
      },
    ],
    queryFn: () =>
      inventoryApi.movements({
        page: movementPage,
        date_from: movementFrom || undefined,
        date_to: movementTo || undefined,
      }),
    enabled: tab === "movimientos",
  });
  async function refreshInventory() {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["lots"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["movements"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["lookup"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["dashboard"],
      }),
    ]);
  }
  const actionProps = {
    canManage,
    onAdjust: setAdjustLot,
    onFractionate: setFractionLot,
    onBlock: setBlockLot,
  };
  return (
    <div className="space-y-4">
      <PageHeader
        title="Inventario"
        description="Trazabilidad por lote: que vence, cuanto queda y cada movimiento registrado."
        actions={
          canManage && (
            <Button
              onClick={() => setEntryOpen(true)}
              icon={<PackagePlus className="size-4" aria-hidden />}
            >
              Registrar entrada
            </Button>
          )
        }
      />

      <div className="flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-white p-1">
        {TABS.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => setTab(option.id)}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              tab === option.id
                ? "bg-brand-700 text-white"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {tab === "vencimientos" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card
            title={
              <span className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-red-600" aria-hidden /> Lotes vencidos
              </span>
            }
            description="Con existencias: hay que darlos de baja."
            padded={false}
          >
            {expiredQuery.isLoading ? (
              <Spinner />
            ) : expiredQuery.isError ? (
              <div className="p-4">
                <ErrorState
                  message={errorMessage(expiredQuery.error)}
                  onRetry={() => void expiredQuery.refetch()}
                />
              </div>
            ) : expiredQuery.data && expiredQuery.data.length > 0 ? (
              <ul className="divide-y divide-slate-100">
                {expiredQuery.data.map((lot) => (
                  <li key={lot.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-slate-900">{lot.product_name}</p>
                      <p className="text-xs text-slate-500">
                        Lote {lot.batch_number} · vencio el {formatDate(lot.expiry_date)} ·{" "}
                        {formatInteger(lot.current_quantity)} u.
                      </p>
                    </div>
                    <Badge tone="danger">Vencido</Badge>
                    <LotActions lot={lot} {...actionProps} />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-4">
                <EmptyState
                  title="Sin lotes vencidos"
                  description="No hay existencias vencidas en este momento."
                />
              </div>
            )}
          </Card>

          <Card
            title={
              <span className="flex items-center gap-2">
                <CalendarClock className="size-4 text-amber-600" aria-hidden /> Vencen en 90 dias
              </span>
            }
            description="Vender primero estos lotes evita perdidas."
            padded={false}
          >
            {expiringQuery.isLoading ? (
              <Spinner />
            ) : expiringQuery.isError ? (
              <div className="p-4">
                <ErrorState
                  message={errorMessage(expiringQuery.error)}
                  onRetry={() => void expiringQuery.refetch()}
                />
              </div>
            ) : expiringQuery.data && expiringQuery.data.length > 0 ? (
              <ul className="divide-y divide-slate-100">
                {expiringQuery.data.map((lot) => (
                  <li key={lot.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-slate-900">{lot.product_name}</p>
                      <p className="text-xs text-slate-500">
                        Lote {lot.batch_number} · vence el {formatDate(lot.expiry_date)} ·{" "}
                        {formatInteger(lot.current_quantity)} u.
                      </p>
                    </div>
                    <ExpiryBadge lot={lot} />
                    <LotActions lot={lot} {...actionProps} />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-4">
                <EmptyState
                  title="Nada por vencer"
                  description="Ningun lote vence en los proximos 90 dias."
                />
              </div>
            )}
          </Card>
        </div>
      )}

      {tab === "lotes" && (
        <Card padded={false}>
          <div className="border-b border-slate-200 p-4">
            <Field label="Buscar lote o producto" htmlFor="lots-search">
              <div className="relative max-w-md">
                <Search
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <Input
                  id="lots-search"
                  placeholder="Numero de lote o nombre…"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  className="pl-9"
                />
              </div>
            </Field>
          </div>

          {lotsQuery.isError ? (
            <div className="p-4">
              <ErrorState
                message={errorMessage(lotsQuery.error)}
                onRetry={() => void lotsQuery.refetch()}
              />
            </div>
          ) : (
            <>
              <Table>
                <THead>
                  <tr>
                    <TH>Producto</TH>
                    <TH>Lote</TH>
                    <TH>Vencimiento</TH>
                    <TH className="text-right">Stock</TH>
                    <TH className="text-right">Costo</TH>
                    <TH>Estado</TH>
                    <TH className="text-right">Acciones</TH>
                  </tr>
                </THead>
                <TBody>
                  {lotsQuery.isLoading ? (
                    <TableMessage colSpan={7}>
                      <Spinner label="Cargando lotes" />
                    </TableMessage>
                  ) : lotsQuery.data && lotsQuery.data.results.length > 0 ? (
                    lotsQuery.data.results.map((lot) => (
                      <TR key={lot.id}>
                        <TD className="font-medium text-slate-900">{lot.product_name}</TD>
                        <TD className="font-mono text-xs">{lot.batch_number}</TD>
                        <TD>{formatDate(lot.expiry_date)}</TD>
                        <TD className="text-right tabular-nums">
                          {formatInteger(lot.current_quantity)}
                        </TD>
                        <TD className="text-right tabular-nums text-slate-500">{lot.cost_price}</TD>
                        <TD>
                          <ExpiryBadge lot={lot} />
                        </TD>
                        <TD>
                          <LotActions lot={lot} {...actionProps} />
                        </TD>
                      </TR>
                    ))
                  ) : (
                    <TableMessage colSpan={7}>
                      <EmptyState
                        title="Sin lotes"
                        description="Registra una entrada de mercaderia para comenzar."
                      />
                    </TableMessage>
                  )}
                </TBody>
              </Table>
              {lotsQuery.data && (
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  count={lotsQuery.data.count}
                  onChange={setPage}
                />
              )}
            </>
          )}
        </Card>
      )}

      {tab === "movimientos" && (
        <Card padded={false}>
          <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Desde" htmlFor="mov-from">
              <Input
                id="mov-from"
                type="date"
                value={movementFrom}
                onChange={(event) => {
                  setMovementFrom(event.target.value);
                  setMovementPage(1);
                }}
              />
            </Field>
            <Field label="Hasta" htmlFor="mov-to">
              <Input
                id="mov-to"
                type="date"
                value={movementTo}
                onChange={(event) => {
                  setMovementTo(event.target.value);
                  setMovementPage(1);
                }}
              />
            </Field>
          </div>

          {movementsQuery.isError ? (
            <div className="p-4">
              <ErrorState
                message={errorMessage(movementsQuery.error)}
                onRetry={() => void movementsQuery.refetch()}
              />
            </div>
          ) : (
            <>
              <Table>
                <THead>
                  <tr>
                    <TH>Fecha</TH>
                    <TH>Tipo</TH>
                    <TH>Producto</TH>
                    <TH>Lote</TH>
                    <TH className="text-right">Variacion</TH>
                    <TH className="text-right">Saldo</TH>
                    <TH>Motivo</TH>
                    <TH>Usuario</TH>
                  </tr>
                </THead>
                <TBody>
                  {movementsQuery.isLoading ? (
                    <TableMessage colSpan={8}>
                      <Spinner label="Cargando movimientos" />
                    </TableMessage>
                  ) : movementsQuery.data && movementsQuery.data.results.length > 0 ? (
                    movementsQuery.data.results.map((movement) => (
                      <TR key={movement.id}>
                        <TD className="whitespace-nowrap">{formatDateTime(movement.created_at)}</TD>
                        <TD>{movement.movement_type_display}</TD>
                        <TD className="font-medium text-slate-900">{movement.product_name}</TD>
                        <TD className="font-mono text-xs">{movement.lot_batch}</TD>
                        <TD
                          className={cn(
                            "text-right font-semibold tabular-nums",
                            movement.quantity_delta > 0 ? "text-brand-700" : "text-red-700",
                          )}
                        >
                          {movement.quantity_delta > 0 ? "+" : ""}
                          {formatInteger(movement.quantity_delta)}
                        </TD>
                        <TD className="text-right tabular-nums">
                          {formatInteger(movement.balance_after)}
                        </TD>
                        <TD className="max-w-56 truncate text-slate-500" title={movement.reason}>
                          {movement.reason || "—"}
                        </TD>
                        <TD className="text-slate-500">{movement.created_by_name}</TD>
                      </TR>
                    ))
                  ) : (
                    <TableMessage colSpan={8}>
                      <EmptyState
                        title="Sin movimientos"
                        description="No hubo movimientos en el periodo."
                      />
                    </TableMessage>
                  )}
                </TBody>
              </Table>
              {movementsQuery.data && (
                <Pagination
                  page={movementPage}
                  pageSize={PAGE_SIZE}
                  count={movementsQuery.data.count}
                  onChange={setMovementPage}
                />
              )}
            </>
          )}

          <div className="border-t border-slate-200 p-4">
            <Alert tone="info">
              El libro de movimientos es inmutable: no se puede editar ni borrar. Las correcciones
              se hacen con un movimiento nuevo y su motivo.
            </Alert>
          </div>
        </Card>
      )}

      <StockEntryModal
        open={entryOpen}
        onClose={() => setEntryOpen(false)}
        onSaved={() => void refreshInventory()}
      />
      <AdjustLotModal
        lot={adjustLot}
        onClose={() => setAdjustLot(null)}
        onSaved={() => void refreshInventory()}
      />
      <FractionationModal
        lot={fractionLot}
        onClose={() => setFractionLot(null)}
        onSaved={() => void refreshInventory()}
      />
      <BlockLotModal
        lot={blockLot}
        onClose={() => setBlockLot(null)}
        onSaved={() => void refreshInventory()}
      />
    </div>
  );
}
