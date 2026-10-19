import { useEffect, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { errorMessage } from "@/api/client";
import { catalogApi } from "@/api/endpoints/catalog";
import { inventoryApi } from "@/api/endpoints/inventory";
import type { Lot } from "@/api/types";
import { Button } from "@/components/Button";
import { Field, Input, Select, Textarea } from "@/components/Field";
import { Alert } from "@/components/Feedback";
import { Modal } from "@/components/Modal";
import { formatDate, formatInteger, formatMoney, todayIso } from "@/lib/format";

const ADJUSTMENT_TYPES = [
  { value: "AJUSTE_POSITIVO", label: "Ajuste positivo (sobrante)", sign: 1 },
  { value: "AJUSTE_NEGATIVO", label: "Ajuste negativo (faltante)", sign: -1 },
  { value: "BAJA_VENCIMIENTO", label: "Baja por vencimiento", sign: -1 },
  { value: "BAJA_AVERIA", label: "Baja por averia o rotura", sign: -1 },
] as const;

function LotSummary({ lot }: { lot: Lot }) {
  return (
    <dl className="grid grid-cols-2 gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm sm:grid-cols-4">
      <div className="col-span-2">
        <dt className="text-xs text-slate-500">Producto</dt>
        <dd className="font-medium text-slate-900">{lot.product_name}</dd>
      </div>
      <div>
        <dt className="text-xs text-slate-500">Lote</dt>
        <dd className="font-mono">{lot.batch_number}</dd>
      </div>
      <div>
        <dt className="text-xs text-slate-500">Stock actual</dt>
        <dd className="font-semibold tabular-nums">{formatInteger(lot.current_quantity)}</dd>
      </div>
      <div>
        <dt className="text-xs text-slate-500">Vence</dt>
        <dd>{formatDate(lot.expiry_date)}</dd>
      </div>
      <div>
        <dt className="text-xs text-slate-500">Costo unitario</dt>
        <dd className="tabular-nums">{formatMoney(lot.cost_price)}</dd>
      </div>
    </dl>
  );
}

/** Ajuste de stock con motivo obligatorio. */
export function AdjustLotModal({
  lot,
  onClose,
  onSaved,
}: {
  lot: Lot | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [type, setType] = useState<string>("AJUSTE_NEGATIVO");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!lot) return;
    setType("AJUSTE_NEGATIVO");
    setQuantity("1");
    setReason("");
    setNotes("");
    setError(null);
  }, [lot]);

  if (!lot) return null;

  const activeLotId = lot.id;
  const sign = ADJUSTMENT_TYPES.find((option) => option.value === type)?.sign ?? -1;
  const delta = sign * Math.abs(Number(quantity) || 0);
  const resulting = lot.current_quantity + delta;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!Number.isInteger(Number(quantity)) || Number(quantity) <= 0) {
      setError("La cantidad debe ser un entero mayor que cero.");
      return;
    }
    if (resulting < 0) {
      setError("El ajuste dejaria el stock en negativo. Revisa la cantidad.");
      return;
    }
    if (!reason.trim()) {
      setError("El motivo es obligatorio: queda en el libro de movimientos.");
      return;
    }

    setSubmitting(true);
    try {
      await inventoryApi.adjust({
        lot: activeLotId,
        quantity_delta: delta,
        reason: reason.trim(),
        notes: notes.trim(),
        movement_type: type,
      });
      onSaved();
      onClose();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Ajustar stock del lote"
      description="Los ajustes mueven inventario sin respaldo documental: por eso exigen motivo."
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="adjust-form" loading={submitting}>
            Registrar ajuste
          </Button>
        </>
      }
    >
      <form id="adjust-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <LotSummary lot={lot} />

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Tipo de movimiento" htmlFor="adjust-type" required>
            <Select id="adjust-type" value={type} onChange={(event) => setType(event.target.value)}>
              {ADJUSTMENT_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Cantidad" htmlFor="adjust-quantity" required>
            <Input
              id="adjust-quantity"
              type="number"
              min={1}
              step={1}
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              className="tabular-nums"
              required
            />
          </Field>
        </div>

        <p className="text-sm text-slate-600">
          Stock resultante:{" "}
          <strong className={resulting < 0 ? "text-red-700" : "text-slate-900"}>
            {formatInteger(resulting)}
          </strong>{" "}
          unidades ({delta > 0 ? "+" : ""}
          {formatInteger(delta)}).
        </p>

        <Field label="Motivo" htmlFor="adjust-reason" required hint="Ej.: frasco roto, conteo fisico, vencido.">
          <Input
            id="adjust-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            maxLength={160}
            required
          />
        </Field>

        <Field label="Notas" htmlFor="adjust-notes">
          <Textarea
            id="adjust-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            maxLength={500}
          />
        </Field>
      </form>
    </Modal>
  );
}

/** Bloqueo de un lote para que no se venda. */
export function BlockLotModal({
  lot,
  onClose,
  onSaved,
}: {
  lot: Lot | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!lot) return;
    setReason("");
    setError(null);
  }, [lot]);

  if (!lot) return null;

  if (lot.is_blocked) {
    return (
      <Modal open onClose={onClose} title="Lote bloqueado" size="sm">
        <Alert tone="warning" title={`Lote ${lot.batch_number}`}>
          Este lote ya esta bloqueado y no se puede vender.
          {lot.block_reason && <p className="mt-1">Motivo: {lot.block_reason}</p>}
        </Alert>
      </Modal>
    );
  }

  const activeLotId = lot.id;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!reason.trim()) {
      setError("Indica por que se bloquea el lote.");
      return;
    }

    setSubmitting(true);
    try {
      await inventoryApi.blockLot(activeLotId, reason.trim());
      onSaved();
      onClose();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Bloquear lote"
      description="Un lote bloqueado no se puede vender, aunque tenga stock y no este vencido."
      size="sm"
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="block-form" variant="danger" loading={submitting}>
            Bloquear lote
          </Button>
        </>
      }
    >
      <form id="block-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <LotSummary lot={lot} />
        <Field label="Motivo del bloqueo" htmlFor="block-reason" required>
          <Input
            id="block-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Sospecha de falsificacion, cadena de frio rota…"
            maxLength={160}
            required
          />
        </Field>
      </form>
    </Modal>
  );
}

/** Fraccionamiento: abrir una caja y convertirla en blisteres o unidades. */
export function FractionationModal({
  lot,
  onClose,
  onSaved,
}: {
  lot: Lot | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [quantity, setQuantity] = useState("1");
  const [batchNumber, setBatchNumber] = useState("");
  const [expiryDate, setExpiryDate] = useState(todayIso());
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const conversionsQuery = useQuery({
    queryKey: ["unit-conversions", lot?.product],
    queryFn: () => catalogApi.unitConversions({ source: lot?.product }),
    enabled: lot !== null,
  });

  useEffect(() => {
    if (!lot) return;
    setQuantity("1");
    setBatchNumber(lot.batch_number);
    setExpiryDate(lot.expiry_date);
    setReason("Fraccionamiento de presentacion");
    setError(null);
  }, [lot]);

  if (!lot) return null;

  const activeLotId = lot.id;
  const availableQuantity = lot.current_quantity;
  const conversion = conversionsQuery.data?.results[0] ?? null;
  const units = conversion ? (Number(quantity) || 0) * conversion.factor : 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!conversion) {
      setError("Este producto no tiene una conversion de presentacion configurada.");
      return;
    }
    if (!Number.isInteger(Number(quantity)) || Number(quantity) <= 0) {
      setError("La cantidad a fraccionar debe ser un entero mayor que cero.");
      return;
    }
    if (Number(quantity) > availableQuantity) {
      setError(`Solo hay ${availableQuantity} unidades de esta presentacion.`);
      return;
    }
    if (!batchNumber.trim()) {
      setError("Indica el numero de lote de la presentacion menor.");
      return;
    }

    setSubmitting(true);
    try {
      await inventoryApi.fractionate({
        source_lot: activeLotId,
        quantity: Number(quantity),
        batch_number: batchNumber.trim(),
        expiry_date: expiryDate,
        reason: reason.trim() || undefined,
      });
      onSaved();
      onClose();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Fraccionar presentacion"
      description="Convierte una presentacion mayor en menor. Genera dos movimientos: salida y entrada."
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button
            type="submit"
            form="fraction-form"
            loading={submitting}
            disabled={!conversion}
          >
            Fraccionar
          </Button>
        </>
      }
    >
      <form id="fraction-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <LotSummary lot={lot} />

        {conversionsQuery.isLoading ? (
          <p className="text-sm text-slate-500">Buscando la conversion configurada…</p>
        ) : conversion ? (
          <Alert tone="info" title="Conversion configurada">
            {conversion.source_label} → {conversion.factor} × {conversion.target_label}
            <p className="mt-1 text-xs">
              {quantity || 0} × {conversion.factor} = <strong>{formatInteger(units)}</strong>{" "}
              unidades de la presentacion menor.
            </p>
          </Alert>
        ) : (
          <Alert tone="warning" title="Sin conversion configurada">
            Antes de fraccionar, administracion debe definir cuantas unidades menores contiene
            esta presentacion (Catalogo → conversiones).
          </Alert>
        )}

        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Cantidad a abrir" htmlFor="fraction-quantity" required>
            <Input
              id="fraction-quantity"
              type="number"
              min={1}
              step={1}
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              className="tabular-nums"
              required
            />
          </Field>
          <Field label="Lote destino" htmlFor="fraction-batch" required>
            <Input
              id="fraction-batch"
              value={batchNumber}
              onChange={(event) => setBatchNumber(event.target.value)}
              maxLength={64}
              required
            />
          </Field>
          <Field label="Vencimiento" htmlFor="fraction-expiry" required>
            <Input
              id="fraction-expiry"
              type="date"
              value={expiryDate}
              onChange={(event) => setExpiryDate(event.target.value)}
              required
            />
          </Field>
        </div>

        <Field label="Motivo" htmlFor="fraction-reason">
          <Input
            id="fraction-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            maxLength={160}
          />
        </Field>
      </form>
    </Modal>
  );
}
