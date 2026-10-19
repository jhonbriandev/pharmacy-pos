import { useEffect, useRef, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { errorMessage } from "@/api/client";
import { inventoryApi } from "@/api/endpoints/inventory";
import { Button } from "@/components/Button";
import { Field, Input, Textarea } from "@/components/Field";
import { Alert } from "@/components/Feedback";
import { Modal } from "@/components/Modal";
import { addDaysIso, formatMoney, todayIso } from "@/lib/format";
import { newRequestId } from "@/lib/ids";
import { ProductPicker } from "./ProductPicker";
function createKey() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Registro de una entrada de mercaderia.
 *
 * Cada linea es un lote con su vencimiento. El backend rechaza dos lineas del
 * mismo producto y lote: sumar en silencio es un error de captura, no una
 * comodidad.
 */
export function StockEntryModal({ open, onClose, onSaved }) {
  const [supplier, setSupplier] = useState("");
  const [documentNumber, setDocumentNumber] = useState("");
  const [receivedAt, setReceivedAt] = useState(todayIso());
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const requestIdRef = useRef(null);
  useEffect(() => {
    if (!open) return;
    setSupplier("");
    setDocumentNumber("");
    setReceivedAt(todayIso());
    setNotes("");
    setItems([]);
    setError(null);
    requestIdRef.current = null;
  }, [open]);
  function addProduct(product) {
    setItems((current) => [
      ...current,
      {
        key: createKey(),
        product,
        batchNumber: "",
        expiryDate: addDaysIso(todayIso(), 365),
        quantity: "1",
        costPrice: product.last_cost,
      },
    ]);
    requestIdRef.current = null;
  }
  function updateItem(key, patch) {
    setItems((current) =>
      current.map((item) =>
        item.key === key
          ? {
              ...item,
              ...patch,
            }
          : item,
      ),
    );
    requestIdRef.current = null;
  }
  function removeItem(key) {
    setItems((current) => current.filter((item) => item.key !== key));
    requestIdRef.current = null;
  }
  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    if (!supplier.trim()) {
      setError("Indica el proveedor.");
      return;
    }
    if (items.length === 0) {
      setError("Agrega al menos un producto a la entrada.");
      return;
    }
    for (const item of items) {
      if (!item.batchNumber.trim()) {
        setError(`Falta el numero de lote de ${item.product.display_name}.`);
        return;
      }
      if (!item.expiryDate) {
        setError(`Falta la fecha de vencimiento de ${item.product.display_name}.`);
        return;
      }
      if (!Number.isInteger(Number(item.quantity)) || Number(item.quantity) < 1) {
        setError(`La cantidad de ${item.product.display_name} debe ser un entero mayor que cero.`);
        return;
      }
      if (item.costPrice === "" || Number(item.costPrice) < 0) {
        setError(`El costo de ${item.product.display_name} no es valido.`);
        return;
      }
    }
    const requestId = requestIdRef.current ?? newRequestId();
    requestIdRef.current = requestId;
    setSubmitting(true);
    try {
      await inventoryApi.createEntry({
        client_request_id: requestId,
        supplier: supplier.trim(),
        document_number: documentNumber.trim(),
        received_at: receivedAt,
        notes: notes.trim(),
        items: items.map((item) => ({
          product: item.product.id,
          batch_number: item.batchNumber.trim(),
          expiry_date: item.expiryDate,
          quantity: Number(item.quantity),
          cost_price: item.costPrice,
        })),
      });
      onSaved();
      onClose();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }
  const estimatedTotal = items.reduce(
    (total, item) => total + Number(item.costPrice || 0) * Number(item.quantity || 0),
    0,
  );
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Registrar entrada de mercaderia"
      description="Cada linea genera un lote con su vencimiento y su movimiento de ingreso."
      size="xl"
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="stock-entry-form" loading={submitting}>
            Registrar entrada
          </Button>
        </>
      }
    >
      <form id="stock-entry-form" onSubmit={handleSubmit} className="space-y-5" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}

        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Proveedor" htmlFor="entry-supplier" required>
            <Input
              id="entry-supplier"
              value={supplier}
              onChange={(event) => setSupplier(event.target.value)}
              placeholder="Distribuidora…"
              maxLength={160}
              required
            />
          </Field>
          <Field label="Documento" htmlFor="entry-document" hint="Factura o guia.">
            <Input
              id="entry-document"
              value={documentNumber}
              onChange={(event) => setDocumentNumber(event.target.value)}
              placeholder="F001-000123"
              maxLength={64}
            />
          </Field>
          <Field label="Fecha de recepcion" htmlFor="entry-date" required>
            <Input
              id="entry-date"
              type="date"
              value={receivedAt}
              onChange={(event) => setReceivedAt(event.target.value)}
              required
            />
          </Field>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">Productos</p>
          <ProductPicker onSelect={addProduct} excludeIds={items.map((item) => item.product.id)} />

          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold tracking-wide text-slate-600 uppercase">
                <tr>
                  <th className="px-3 py-2">Producto</th>
                  <th className="px-3 py-2">Lote</th>
                  <th className="px-3 py-2">Vence</th>
                  <th className="px-3 py-2">Cant.</th>
                  <th className="px-3 py-2">Costo unit.</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                      Busca un producto arriba para agregarlo a la entrada.
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr key={item.key}>
                      <td className="min-w-56 px-3 py-2">
                        <p className="font-medium text-slate-900">{item.product.display_name}</p>
                        <p className="text-xs text-slate-500">
                          {item.product.barcode ?? "sin codigo"}
                        </p>
                      </td>
                      <td className="px-3 py-2">
                        <Input
                          aria-label={`Lote de ${item.product.display_name}`}
                          value={item.batchNumber}
                          onChange={(event) =>
                            updateItem(item.key, {
                              batchNumber: event.target.value,
                            })
                          }
                          maxLength={64}
                          required
                        />
                      </td>
                      <td className="px-3 py-2">
                        <Input
                          aria-label={`Vencimiento de ${item.product.display_name}`}
                          type="date"
                          value={item.expiryDate}
                          onChange={(event) =>
                            updateItem(item.key, {
                              expiryDate: event.target.value,
                            })
                          }
                          required
                        />
                      </td>
                      <td className="w-24 px-3 py-2">
                        <Input
                          aria-label={`Cantidad de ${item.product.display_name}`}
                          type="number"
                          min={1}
                          step={1}
                          value={item.quantity}
                          onChange={(event) =>
                            updateItem(item.key, {
                              quantity: event.target.value,
                            })
                          }
                          className="text-right tabular-nums"
                          required
                        />
                      </td>
                      <td className="w-32 px-3 py-2">
                        <Input
                          aria-label={`Costo de ${item.product.display_name}`}
                          inputMode="decimal"
                          value={item.costPrice}
                          onChange={(event) =>
                            updateItem(item.key, {
                              costPrice: event.target.value,
                            })
                          }
                          className="text-right tabular-nums"
                          required
                        />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeItem(item.key)}
                          aria-label={`Quitar ${item.product.display_name}`}
                          icon={<Trash2 className="size-4 text-slate-500" aria-hidden />}
                        />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {items.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-4 py-3 text-sm">
            <span className="text-slate-600">
              {items.length} linea(s) · costo estimado{" "}
              <strong className="tabular-nums">{formatMoney(estimatedTotal)}</strong>
            </span>
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <Plus className="size-3.5" aria-hidden /> El costo real lo confirma la factura
            </span>
          </div>
        )}

        <Field label="Observaciones de la entrada" htmlFor="entry-notes-long">
          <Textarea
            id="entry-notes-long"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Opcional: incidencias de la recepcion"
            maxLength={500}
          />
        </Field>
      </form>
    </Modal>
  );
}
