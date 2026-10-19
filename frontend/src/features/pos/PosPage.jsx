import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Banknote,
  CreditCard,
  Minus,
  Plus,
  Printer,
  Search,
  ShoppingCart,
  Trash2,
  Wallet,
} from "lucide-react";
import { ApiError, errorMessage } from "@/api/client";
import { catalogApi } from "@/api/endpoints/catalog";
import { salesApi } from "@/api/endpoints/sales";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Input } from "@/components/Field";
import { Alert, Spinner } from "@/components/Feedback";
import { Modal } from "@/components/Modal";
import {
  cartQuantity,
  cartTotalCents,
  formatCents,
  fromCents,
  toCents,
  toSaleItems,
} from "@/lib/cart";
import { cn } from "@/lib/cn";
import { formatMoney } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";
import { newRequestId } from "@/lib/ids";
import { ReceiptTicket } from "@/features/sales/ReceiptTicket";
const PAYMENT_METHODS = [
  {
    value: "EFECTIVO",
    label: "Efectivo",
    icon: Banknote,
  },
  {
    value: "TARJETA",
    label: "Tarjeta",
    icon: CreditCard,
  },
  {
    value: "TRANSFERENCIA",
    label: "Transferencia",
    icon: Wallet,
  },
];
const QUICK_AMOUNTS = [10, 20, 50, 100];
function toCartLine(product) {
  return {
    productId: product.id,
    name: product.display_name,
    unitPrice: product.sale_price,
    quantity: 1,
    availableStock: product.stock,
    presentation: product.presentation_display,
    unitLabel: product.display_name,
  };
}
export function PosPage() {
  const queryClient = useQueryClient();
  const searchRef = useRef(null);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query.trim(), 250);
  const [lines, setLines] = useState([]);
  const [method, setMethod] = useState("EFECTIVO");
  const [received, setReceived] = useState("");
  const [reference, setReference] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [receiptNumber, setReceiptNumber] = useState(null);

  /**
   * Identificador de la peticion en curso.
   *
   * Se conserva si el envio falla para que reintentar devuelva la venta ya
   * creada (si alcanzo a crearse) en lugar de cobrarla dos veces.
   */
  const requestIdRef = useRef(null);
  const searchResults = useQuery({
    queryKey: ["lookup", debouncedQuery],
    queryFn: () => catalogApi.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 15_000,
  });
  const receiptQuery = useQuery({
    queryKey: ["receipt", receiptNumber],
    queryFn: () => salesApi.receipt(receiptNumber),
    enabled: receiptNumber !== null,
    staleTime: Infinity,
  });
  const totalCents = useMemo(() => cartTotalCents(lines), [lines]);
  const itemCount = useMemo(() => cartQuantity(lines), [lines]);
  const receivedCents = toCents(received || "0");
  const changeCents = Math.max(0, receivedCents - totalCents);
  const canCharge =
    lines.length > 0 && (method !== "EFECTIVO" || receivedCents >= totalCents) && !submitting;

  // Al cerrar la boleta, el cursor vuelve al buscador para la siguiente venta.
  useEffect(() => {
    if (receiptNumber === null) searchRef.current?.focus();
  }, [receiptNumber]);
  function resetSaleState() {
    requestIdRef.current = null;
    setLines([]);
    setReceived("");
    setReference("");
    setMethod("EFECTIVO");
  }
  function addProduct(product) {
    setSuccess(null);
    setError(null);
    if (product.stock <= 0) {
      setError(`${product.display_name} no tiene stock vendible (lote vencido o sin existencias).`);
      return;
    }
    const existing = lines.find((line) => line.productId === product.id);
    if (existing && existing.quantity + 1 > product.stock) {
      setError(`Solo hay ${product.stock} unidades disponibles de ${product.display_name}.`);
      return;
    }
    requestIdRef.current = null;
    setLines((current) =>
      existing
        ? current.map((line) =>
            line.productId === product.id
              ? {
                  ...line,
                  quantity: line.quantity + 1,
                }
              : line,
          )
        : [...current, toCartLine(product)],
    );
    setQuery("");
  }
  function setQuantity(productId, quantity) {
    if (quantity <= 0) {
      removeLine(productId);
      return;
    }
    requestIdRef.current = null;
    setLines((current) =>
      current.map((line) =>
        line.productId === productId
          ? {
              ...line,
              quantity: Math.min(quantity, line.availableStock),
            }
          : line,
      ),
    );
  }
  function removeLine(productId) {
    requestIdRef.current = null;
    setLines((current) => current.filter((line) => line.productId !== productId));
  }
  async function handleScanSubmit(event) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const code = query.trim();
    if (!code) return;
    try {
      const product = await catalogApi.byBarcode(code);
      addProduct(product);
    } catch (caught) {
      // Si no era un codigo de barras, se acepta el primer resultado de texto.
      const first = searchResults.data?.[0];
      if (caught instanceof ApiError && caught.status === 404 && first) {
        addProduct(first);
        return;
      }
      if (caught instanceof ApiError && caught.status === 404) {
        setError(`No existe un producto activo con el codigo ${code}.`);
        return;
      }
      setError(errorMessage(caught));
    }
  }
  async function handleCheckout() {
    if (lines.length === 0) return;
    setError(null);
    setSubmitting(true);
    const requestId = requestIdRef.current ?? newRequestId();
    requestIdRef.current = requestId;
    try {
      const sale = await salesApi.create({
        client_request_id: requestId,
        items: toSaleItems(lines),
        payment: {
          method,
          received_amount: method === "EFECTIVO" ? fromCents(receivedCents) : null,
          reference: reference.trim() || undefined,
        },
      });
      resetSaleState();
      setReceiptNumber(sale.number);
      setSuccess(`Venta ${sale.number} registrada por ${formatMoney(sale.total)}.`);

      // El stock cambio: la proxima busqueda debe traer existencias reales.
      await queryClient.invalidateQueries({
        queryKey: ["lookup"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["dashboard"],
      });
    } catch (caught) {
      requestIdRef.current = null;
      setError(errorMessage(caught));
      await queryClient.invalidateQueries({
        queryKey: ["lookup"],
      });
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Punto de venta</h1>
          <p className="mt-1 text-sm text-slate-500">
            Escanea el codigo de barras o busca por nombre. El lote mas proximo a vencer sale
            primero.
          </p>
        </div>
        {lines.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={resetSaleState}
            icon={<Trash2 className="size-4" />}
          >
            Vaciar carrito
          </Button>
        )}
      </div>

      {error && (
        <Alert tone="danger" title="No se pudo completar la operacion">
          {error}
        </Alert>
      )}
      {success && <Alert tone="success">{success}</Alert>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-4">
          <Card padded={false}>
            <div className="p-4">
              <label htmlFor="pos-search" className="sr-only">
                Buscar producto
              </label>
              <div className="relative">
                <Search
                  className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-slate-400"
                  aria-hidden
                />
                <Input
                  id="pos-search"
                  ref={searchRef}
                  autoFocus
                  autoComplete="off"
                  placeholder="Codigo de barras o nombre del producto…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleScanSubmit}
                  className="h-12 pl-11 text-base"
                />
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Enter agrega el producto. Para buscar por nombre escribe al menos dos letras.
              </p>
            </div>

            {debouncedQuery.length >= 2 && (
              <div className="border-t border-slate-200">
                {searchResults.isFetching ? (
                  <Spinner label="Buscando" />
                ) : searchResults.data && searchResults.data.length > 0 ? (
                  <ul className="max-h-72 divide-y divide-slate-100 overflow-y-auto">
                    {searchResults.data.map((product) => (
                      <li key={product.id}>
                        <button
                          type="button"
                          onClick={() => addProduct(product)}
                          disabled={product.stock <= 0}
                          className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <span className="min-w-0">
                            <span className="block truncate font-medium text-slate-900">
                              {product.display_name}
                            </span>
                            <span className="block text-xs text-slate-500">
                              {product.barcode ?? "sin codigo"} · stock {product.stock}
                            </span>
                          </span>
                          <span className="flex shrink-0 items-center gap-2">
                            <span className="font-semibold tabular-nums">
                              {formatMoney(product.sale_price)}
                            </span>
                            {product.stock <= 0 ? (
                              <Badge tone="danger">Sin stock</Badge>
                            ) : (
                              <Plus className="size-4 text-brand-700" aria-hidden />
                            )}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="px-4 py-6 text-center text-sm text-slate-500">
                    No se encontraron productos activos.
                  </p>
                )}
              </div>
            )}
          </Card>

          <Card
            title="Carrito"
            description={itemCount > 0 ? `${itemCount} unidad(es)` : undefined}
            padded={false}
          >
            {lines.length === 0 ? (
              <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
                <ShoppingCart className="size-8 text-slate-300" aria-hidden />
                <p className="font-medium text-slate-700">El carrito esta vacio</p>
                <p className="max-w-sm text-sm text-slate-500">
                  Escanea un producto o buscalo por nombre para comenzar la venta.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {lines.map((line) => (
                  <li key={line.productId} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-slate-900">{line.name}</p>
                      <p className="text-xs text-slate-500">
                        {formatMoney(line.unitPrice)} c/u · stock {line.availableStock}
                      </p>
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-label={`Quitar una unidad de ${line.name}`}
                        onClick={() => setQuantity(line.productId, line.quantity - 1)}
                        icon={<Minus className="size-4" aria-hidden />}
                      />
                      <input
                        aria-label={`Cantidad de ${line.name}`}
                        type="number"
                        min={1}
                        max={line.availableStock}
                        value={line.quantity}
                        onChange={(event) =>
                          setQuantity(line.productId, Number(event.target.value) || 0)
                        }
                        className="h-9 w-16 rounded-lg border border-slate-300 text-center text-sm tabular-nums shadow-sm"
                      />
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-label={`Agregar una unidad de ${line.name}`}
                        onClick={() => setQuantity(line.productId, line.quantity + 1)}
                        disabled={line.quantity >= line.availableStock}
                        icon={<Plus className="size-4" aria-hidden />}
                      />
                    </div>

                    <p className="w-24 text-right font-semibold tabular-nums">
                      {formatCents(toCents(line.unitPrice) * line.quantity)}
                    </p>

                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`Quitar ${line.name} del carrito`}
                      onClick={() => removeLine(line.productId)}
                      icon={<Trash2 className="size-4 text-slate-500" aria-hidden />}
                    />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        {/* Panel de cobro */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <Card title="Cobro">
            <div className="space-y-4">
              <div className="rounded-lg bg-slate-900 px-4 py-3 text-white">
                <p className="text-xs tracking-wide text-slate-300 uppercase">Total a pagar</p>
                <p className="mt-1 text-3xl font-semibold tabular-nums">
                  {formatCents(totalCents)}
                </p>
                <p className="mt-0.5 text-xs text-slate-400">
                  {itemCount} unidad(es) · precios con IGV incluido
                </p>
              </div>

              <fieldset disabled={submitting}>
                <legend className="mb-2 text-sm font-medium text-slate-700">Medio de pago</legend>
                <div className="grid grid-cols-3 gap-2">
                  {PAYMENT_METHODS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setMethod(option.value)}
                      className={cn(
                        "flex flex-col items-center gap-1 rounded-lg border px-2 py-2 text-xs font-medium transition-colors",
                        method === option.value
                          ? "border-brand-600 bg-brand-50 text-brand-800"
                          : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50",
                      )}
                      aria-pressed={method === option.value}
                    >
                      <option.icon className="size-4" aria-hidden />
                      {option.label}
                    </button>
                  ))}
                </div>
              </fieldset>

              {method === "EFECTIVO" ? (
                <div className="space-y-2">
                  <label htmlFor="received" className="text-sm font-medium text-slate-700">
                    Efectivo recibido
                  </label>
                  <Input
                    id="received"
                    inputMode="decimal"
                    placeholder="0.00"
                    value={received}
                    onChange={(event) => setReceived(event.target.value.replace(/[^\d.]/g, ""))}
                    className="h-12 text-lg tabular-nums"
                    disabled={submitting}
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setReceived(fromCents(totalCents))}
                    >
                      Exacto
                    </Button>
                    {QUICK_AMOUNTS.map((amount) => (
                      <Button
                        key={amount}
                        variant="secondary"
                        size="sm"
                        onClick={() => setReceived(String(amount))}
                        disabled={amount * 100 < totalCents}
                      >
                        S/ {amount}
                      </Button>
                    ))}
                  </div>
                  <p className="flex justify-between text-sm">
                    <span className="text-slate-600">Vuelto</span>
                    <span className="font-semibold tabular-nums">{formatCents(changeCents)}</span>
                  </p>
                  {receivedCents > 0 && receivedCents < totalCents && (
                    <p className="text-xs font-medium text-amber-700">
                      Faltan {formatCents(totalCents - receivedCents)} para cubrir el total.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <label htmlFor="reference" className="text-sm font-medium text-slate-700">
                    Referencia (opcional)
                  </label>
                  <Input
                    id="reference"
                    placeholder={
                      method === "TARJETA" ? "Nro. de operacion del POS" : "Nro. de operacion"
                    }
                    value={reference}
                    onChange={(event) => setReference(event.target.value)}
                    maxLength={64}
                    disabled={submitting}
                  />
                </div>
              )}

              <Button
                size="lg"
                fullWidth
                onClick={handleCheckout}
                loading={submitting}
                disabled={!canCharge}
              >
                Cobrar {formatCents(totalCents)}
              </Button>

              {lines.length > 0 && !canCharge && method === "EFECTIVO" && (
                <p className="text-center text-xs text-slate-500">
                  Ingresa el efectivo recibido para continuar.
                </p>
              )}
            </div>
          </Card>
        </div>
      </div>

      <Modal
        open={receiptNumber !== null}
        onClose={() => setReceiptNumber(null)}
        title="Venta registrada"
        description={`Boleta ${receiptNumber ?? ""}`}
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setReceiptNumber(null)}>
              Nueva venta
            </Button>
            <Button onClick={() => window.print()} icon={<Printer className="size-4" />}>
              Imprimir
            </Button>
          </>
        }
      >
        {receiptQuery.isLoading ? (
          <Spinner label="Preparando la boleta" />
        ) : receiptQuery.data ? (
          <ReceiptTicket receipt={receiptQuery.data} />
        ) : (
          <p className="text-sm text-slate-500">No se pudo cargar la boleta.</p>
        )}
      </Modal>
    </div>
  );
}
