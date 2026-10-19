import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Pill, Plus, Search } from "lucide-react";
import { errorMessage } from "@/api/client";
import { catalogApi } from "@/api/endpoints/catalog";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card, PageHeader } from "@/components/Card";
import { Field, Input, Select } from "@/components/Field";
import { EmptyState, ErrorState, Spinner } from "@/components/Feedback";
import { Pagination, Table, TBody, TD, TH, THead, TR, TableMessage } from "@/components/Table";
import { useAuth } from "@/features/auth/context";
import { formatInteger, formatMoney } from "@/lib/format";
import { useDebouncedValue } from "@/lib/hooks";
import { GroupFormModal, ProductFormModal } from "./ProductFormModal";
const PAGE_SIZE = 25;
export function CatalogPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canEdit = user?.capabilities.can_manage_catalog ?? false;
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [presentation, setPresentation] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, presentation, activeFilter]);
  const productsQuery = useQuery({
    queryKey: [
      "products",
      {
        page,
        search: debouncedSearch,
        presentation,
        activeFilter,
      },
    ],
    queryFn: () =>
      catalogApi.products({
        page,
        search: debouncedSearch || undefined,
        presentation: presentation || undefined,
        is_active: activeFilter === "" ? undefined : activeFilter === "true",
      }),
  });
  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["products"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["product-groups"],
      }),
      queryClient.invalidateQueries({
        queryKey: ["lookup"],
      }),
    ]);
  }
  function openCreate() {
    setEditing(null);
    setProductModalOpen(true);
  }
  function openEdit(product) {
    setEditing(product);
    setProductModalOpen(true);
  }
  return (
    <div className="space-y-4">
      <PageHeader
        title="Catalogo"
        description="Medicamentos y sus presentaciones vendibles, con precio vigente y stock."
        actions={
          canEdit && (
            <>
              <Button
                variant="secondary"
                onClick={() => setGroupModalOpen(true)}
                icon={<Pill className="size-4" aria-hidden />}
              >
                Nuevo medicamento
              </Button>
              <Button onClick={openCreate} icon={<Plus className="size-4" aria-hidden />}>
                Nuevo producto
              </Button>
            </>
          )
        }
      />

      <Card padded={false}>
        <div className="grid gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Buscar" htmlFor="catalog-search" className="lg:col-span-2">
            <div className="relative">
              <Search
                className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400"
                aria-hidden
              />
              <Input
                id="catalog-search"
                placeholder="Nombre, concentracion o codigo de barras…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="pl-9"
              />
            </div>
          </Field>
          <Field label="Presentacion" htmlFor="catalog-presentation">
            <Select
              id="catalog-presentation"
              value={presentation}
              onChange={(event) => setPresentation(event.target.value)}
            >
              <option value="">Todas</option>
              <option value="CAJA">Caja</option>
              <option value="BLISTER">Blister</option>
              <option value="UNIDAD">Unidad</option>
              <option value="FRASCO">Frasco</option>
              <option value="TUBO">Tubo</option>
              <option value="AMPOLLA">Ampolla</option>
              <option value="SOBRE">Sobre</option>
              <option value="OTRO">Otro</option>
            </Select>
          </Field>
          <Field label="Estado" htmlFor="catalog-active">
            <Select
              id="catalog-active"
              value={activeFilter}
              onChange={(event) => setActiveFilter(event.target.value)}
            >
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </Select>
          </Field>
        </div>

        {productsQuery.isError ? (
          <div className="p-4">
            <ErrorState
              message={errorMessage(productsQuery.error)}
              onRetry={() => void productsQuery.refetch()}
            />
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <TH>Producto</TH>
                  <TH>Presentacion</TH>
                  <TH>Codigo</TH>
                  <TH className="text-right">Precio</TH>
                  <TH className="text-right">Costo</TH>
                  <TH className="text-right">Margen</TH>
                  <TH className="text-right">Stock</TH>
                  <TH className="text-right">Min.</TH>
                  <TH>Estado</TH>
                  {canEdit && <TH className="text-right">Acciones</TH>}
                </tr>
              </THead>
              <TBody>
                {productsQuery.isLoading ? (
                  <TableMessage colSpan={canEdit ? 10 : 9}>
                    <Spinner label="Cargando catalogo" />
                  </TableMessage>
                ) : productsQuery.data && productsQuery.data.results.length > 0 ? (
                  productsQuery.data.results.map((product) => {
                    const belowMinimum = product.min_stock > 0 && product.stock < product.min_stock;
                    return (
                      <TR key={product.id}>
                        <TD className="font-medium text-slate-900">{product.display_name}</TD>
                        <TD>
                          {product.presentation_display}
                          {product.presentation_detail && (
                            <span className="text-slate-500"> {product.presentation_detail}</span>
                          )}
                        </TD>
                        <TD className="font-mono text-xs text-slate-500">
                          {product.barcode ?? "—"}
                        </TD>
                        <TD className="text-right font-semibold tabular-nums">
                          {formatMoney(product.sale_price)}
                        </TD>
                        <TD className="text-right tabular-nums text-slate-500">
                          {formatMoney(product.last_cost)}
                        </TD>
                        <TD
                          className={
                            Number(product.margin) >= 0
                              ? "text-right tabular-nums text-brand-700"
                              : "text-right tabular-nums text-red-700"
                          }
                        >
                          {formatMoney(product.margin)}
                        </TD>
                        <TD className="text-right tabular-nums">
                          <span
                            className={belowMinimum ? "font-semibold text-amber-700" : undefined}
                          >
                            {formatInteger(product.stock)}
                          </span>
                        </TD>
                        <TD className="text-right tabular-nums text-slate-500">
                          {formatInteger(product.min_stock)}
                        </TD>
                        <TD>
                          {product.is_active ? (
                            belowMinimum ? (
                              <Badge tone="warning">Reponer</Badge>
                            ) : (
                              <Badge tone="success">Activo</Badge>
                            )
                          ) : (
                            <Badge tone="neutral">Inactivo</Badge>
                          )}
                        </TD>
                        {canEdit && (
                          <TD className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEdit(product)}
                              aria-label={`Editar ${product.display_name}`}
                              icon={<Pencil className="size-4" aria-hidden />}
                            />
                          </TD>
                        )}
                      </TR>
                    );
                  })
                ) : (
                  <TableMessage colSpan={canEdit ? 10 : 9}>
                    <EmptyState
                      title="Sin productos"
                      description="Crea un medicamento y luego sus presentaciones vendibles."
                    />
                  </TableMessage>
                )}
              </TBody>
            </Table>
            {productsQuery.data && (
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                count={productsQuery.data.count}
                onChange={setPage}
              />
            )}
          </>
        )}
      </Card>

      <ProductFormModal
        open={productModalOpen}
        product={editing}
        onClose={() => setProductModalOpen(false)}
        onSaved={() => void refresh()}
      />
      <GroupFormModal
        open={groupModalOpen}
        onClose={() => setGroupModalOpen(false)}
        onSaved={() => void refresh()}
      />
    </div>
  );
}
