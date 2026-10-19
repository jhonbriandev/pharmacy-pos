import { useEffect, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { errorMessage } from "@/api/client";
import { catalogApi } from "@/api/endpoints/catalog";
import type { Product } from "@/api/types";
import { Alert } from "@/components/Feedback";
import { Button } from "@/components/Button";
import { Field, Input, Select, Textarea } from "@/components/Field";
import { Modal } from "@/components/Modal";
import { formatMoney } from "@/lib/format";

const PRESENTATIONS = [
  { value: "CAJA", label: "Caja" },
  { value: "BLISTER", label: "Blister" },
  { value: "UNIDAD", label: "Unidad" },
  { value: "FRASCO", label: "Frasco" },
  { value: "TUBO", label: "Tubo" },
  { value: "AMPOLLA", label: "Ampolla" },
  { value: "SOBRE", label: "Sobre" },
  { value: "OTRO", label: "Otro" },
];

const FORMS = [
  { value: "TABLETA", label: "Tableta" },
  { value: "CAPSULA", label: "Capsula" },
  { value: "JARABE", label: "Jarabe" },
  { value: "SUSPENSION", label: "Suspension" },
  { value: "SOLUCION", label: "Solucion" },
  { value: "CREMA", label: "Crema" },
  { value: "GEL", label: "Gel" },
  { value: "GOTAS", label: "Gotas" },
  { value: "INYECTABLE", label: "Inyectable" },
  { value: "SUPOSITORIO", label: "Supositorio" },
  { value: "POLVO", label: "Polvo" },
  { value: "UNGUENTO", label: "Unguento" },
];

/** Alta y edicion de un producto (una presentacion vendible concreta). */
export function ProductFormModal({
  open,
  product,
  onClose,
  onSaved,
}: {
  open: boolean;
  product: Product | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = product !== null;

  const [groupId, setGroupId] = useState("");
  const [presentation, setPresentation] = useState("CAJA");
  const [presentationDetail, setPresentationDetail] = useState("");
  const [barcode, setBarcode] = useState("");
  const [unitLabel, setUnitLabel] = useState("");
  const [salePrice, setSalePrice] = useState("");
  const [taxRate, setTaxRate] = useState("18.00");
  const [minStock, setMinStock] = useState("0");
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const groupsQuery = useQuery({
    queryKey: ["product-groups", "options"],
    queryFn: () => catalogApi.groups({ page_size: 100 }),
    enabled: open && !isEdit,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (product) {
      setGroupId(String(product.group));
      setPresentation(product.presentation);
      setPresentationDetail(product.presentation_detail);
      setBarcode(product.barcode ?? "");
      setUnitLabel(product.unit_label);
      setSalePrice(product.sale_price);
      setTaxRate(product.tax_rate);
      setMinStock(String(product.min_stock));
      setIsActive(product.is_active);
    } else {
      setGroupId("");
      setPresentation("CAJA");
      setPresentationDetail("");
      setBarcode("");
      setUnitLabel("");
      setSalePrice("");
      setTaxRate("18.00");
      setMinStock("0");
      setIsActive(true);
    }
  }, [open, product]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!isEdit && !groupId) {
      setError("Selecciona el medicamento (grupo) al que pertenece esta presentacion.");
      return;
    }
    if (!salePrice || Number(salePrice) <= 0) {
      setError("El precio de venta debe ser mayor que cero.");
      return;
    }
    if (Number(minStock) < 0 || !Number.isInteger(Number(minStock))) {
      setError("El stock minimo debe ser un entero no negativo.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        presentation,
        presentation_detail: presentationDetail.trim(),
        barcode: barcode.trim() || null,
        unit_label: unitLabel.trim(),
        sale_price: Number(salePrice).toFixed(2),
        tax_rate: Number(taxRate || 18).toFixed(2),
        min_stock: Number(minStock),
        is_active: isActive,
      };

      if (product) {
        await catalogApi.updateProduct(product.id, payload);
      } else {
        await catalogApi.createProduct({ ...payload, group: Number(groupId) });
      }
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
      open={open}
      onClose={onClose}
      title={isEdit ? "Editar producto" : "Nuevo producto"}
      description={
        isEdit
          ? product?.display_name
          : "Cada presentacion (caja, blister, unidad) es un producto vendible distinto."
      }
      size="lg"
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="product-form" loading={submitting}>
            {isEdit ? "Guardar cambios" : "Crear producto"}
          </Button>
        </>
      }
    >
      <form id="product-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}

        {isEdit ? (
          <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <p className="font-medium text-slate-900">{product?.group_name}</p>
            <p className="text-xs text-slate-500">
              {product?.presentation_display} {product?.presentation_detail} · stock actual{" "}
              {product?.stock} · margen {formatMoney(product?.margin ?? "0")}
            </p>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Medicamento (grupo)" htmlFor="product-group" required>
              <Select
                id="product-group"
                value={groupId}
                onChange={(event) => setGroupId(event.target.value)}
                required
              >
                <option value="">Selecciona…</option>
                {groupsQuery.data?.results.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.display_name}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="flex items-end">
              <p className="text-xs text-slate-500">
                ¿No aparece? Crea primero el medicamento con el boton «Nuevo medicamento».
              </p>
            </div>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Presentacion" htmlFor="product-presentation" required>
            <Select
              id="product-presentation"
              value={presentation}
              onChange={(event) => setPresentation(event.target.value)}
              disabled={isEdit}
            >
              {PRESENTATIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Detalle" htmlFor="product-detail" hint="Ej.: x 100, x 10 tabletas.">
            <Input
              id="product-detail"
              value={presentationDetail}
              onChange={(event) => setPresentationDetail(event.target.value)}
              maxLength={60}
            />
          </Field>
          <Field label="Codigo de barras" htmlFor="product-barcode">
            <Input
              id="product-barcode"
              value={barcode}
              onChange={(event) => setBarcode(event.target.value)}
              maxLength={64}
              placeholder="7751234500011"
            />
          </Field>
          <Field label="Unidad" htmlFor="product-unit" hint="Se muestra en la boleta: tableta, capsula…">
            <Input
              id="product-unit"
              value={unitLabel}
              onChange={(event) => setUnitLabel(event.target.value)}
              maxLength={30}
            />
          </Field>
          <Field label="Precio de venta (S/)" htmlFor="product-price" required hint="Con IGV incluido.">
            <Input
              id="product-price"
              inputMode="decimal"
              value={salePrice}
              onChange={(event) => setSalePrice(event.target.value.replace(/[^\d.]/g, ""))}
              className="tabular-nums"
              required
            />
          </Field>
          <Field label="IGV (%)" htmlFor="product-tax">
            <Input
              id="product-tax"
              inputMode="decimal"
              value={taxRate}
              onChange={(event) => setTaxRate(event.target.value.replace(/[^\d.]/g, ""))}
              className="tabular-nums"
            />
          </Field>
          <Field label="Stock minimo" htmlFor="product-min" hint="Para la alerta de reposicion.">
            <Input
              id="product-min"
              type="number"
              min={0}
              step={1}
              value={minStock}
              onChange={(event) => setMinStock(event.target.value)}
              className="tabular-nums"
            />
          </Field>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(event) => setIsActive(event.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Producto activo (vendible)
            </label>
          </div>
        </div>

        <p className="text-xs text-slate-500">
          El costo no se edita aqui: se actualiza solo al registrar una entrada de mercaderia.
        </p>
      </form>
    </Modal>
  );
}

/** Alta de un medicamento (grupo de presentaciones). */
export function GroupFormModal({
  open,
  onClose,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [concentration, setConcentration] = useState("");
  const [form, setForm] = useState("TABLETA");
  const [laboratory, setLaboratory] = useState("");
  const [category, setCategory] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const laboratoriesQuery = useQuery({
    queryKey: ["laboratories", "options"],
    queryFn: () => catalogApi.laboratories({ page_size: 100 }),
    enabled: open,
    staleTime: 60_000,
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories", "options"],
    queryFn: () => catalogApi.categories({ page_size: 100 }),
    enabled: open,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!open) return;
    setName("");
    setConcentration("");
    setForm("TABLETA");
    setLaboratory("");
    setCategory("");
    setNotes("");
    setError(null);
  }, [open]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError("El nombre del medicamento es obligatorio.");
      return;
    }

    setSubmitting(true);
    try {
      await catalogApi.createGroup({
        name: name.trim(),
        concentration: concentration.trim(),
        pharmaceutical_form: form,
        laboratory: laboratory ? Number(laboratory) : null,
        category: category ? Number(category) : null,
        notes: notes.trim(),
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
      open={open}
      onClose={onClose}
      title="Nuevo medicamento"
      description="Agrupa sus presentaciones: caja, blister y unidad comparten este registro."
      dismissible={!submitting}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="group-form" loading={submitting}>
            Crear medicamento
          </Button>
        </>
      }
    >
      <form id="group-form" onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert tone="danger">{error}</Alert>}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Nombre" htmlFor="group-name" required>
            <Input
              id="group-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Paracetamol"
              maxLength={160}
              required
            />
          </Field>
          <Field label="Concentracion" htmlFor="group-concentration">
            <Input
              id="group-concentration"
              value={concentration}
              onChange={(event) => setConcentration(event.target.value)}
              placeholder="500 mg"
              maxLength={60}
            />
          </Field>
          <Field label="Forma farmaceutica" htmlFor="group-form" required>
            <Select id="group-form" value={form} onChange={(event) => setForm(event.target.value)}>
              {FORMS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Laboratorio" htmlFor="group-lab">
            <Select
              id="group-lab"
              value={laboratory}
              onChange={(event) => setLaboratory(event.target.value)}
            >
              <option value="">Sin especificar</option>
              {laboratoriesQuery.data?.results.map((lab) => (
                <option key={lab.id} value={lab.id}>
                  {lab.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Categoria" htmlFor="group-category">
            <Select
              id="group-category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="">Sin especificar</option>
              {categoriesQuery.data?.results.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field label="Notas" htmlFor="group-notes">
          <Textarea
            id="group-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            maxLength={500}
          />
        </Field>
      </form>
    </Modal>
  );
}
