/** Endpoints del catalogo de productos. */

import { apiRequest } from "../client";
import type {
  ActiveIngredient,
  Category,
  Laboratory,
  Lot,
  Paginated,
  Product,
  ProductGroup,
  ProductLookup,
  UnitConversion,
} from "../types";

export interface ProductListParams {
  search?: string;
  is_active?: boolean;
  presentation?: string;
  group?: number;
  page?: number;
}

export interface ProductPayload {
  group: number;
  presentation: string;
  presentation_detail?: string;
  barcode?: string | null;
  unit_label?: string;
  sale_price: string;
  tax_rate?: string;
  min_stock?: number;
  is_active?: boolean;
}

export interface ProductGroupPayload {
  name: string;
  concentration?: string;
  pharmaceutical_form: string;
  laboratory?: number | null;
  category?: number | null;
  ingredient_ids?: number[];
  notes?: string;
  is_active?: boolean;
}

export const catalogApi = {
  products: (params: ProductListParams = {}) =>
    apiRequest<Paginated<Product>>("/products/", {
      query: {
        search: params.search,
        is_active: params.is_active,
        presentation: params.presentation,
        group: params.group,
        page: params.page,
      },
    }),

  product: (id: number) => apiRequest<Product>(`/products/${id}/`),

  createProduct: (payload: ProductPayload) =>
    apiRequest<Product>("/products/", { method: "POST", body: payload }),

  updateProduct: (id: number, payload: Partial<ProductPayload>) =>
    apiRequest<Product>(`/products/${id}/`, { method: "PATCH", body: payload }),

  productLots: (id: number) => apiRequest<Lot[]>(`/products/${id}/lots/`),

  /** Busqueda por texto: devuelve hasta 20 productos activos. */
  search: (query: string) =>
    apiRequest<ProductLookup[]>("/products/lookup/", { query: { q: query } }),

  /** Lectura de codigo de barras: devuelve uno o falla con 404. */
  byBarcode: (barcode: string) =>
    apiRequest<ProductLookup>("/products/lookup/", { query: { barcode } }),

  lowStock: () => apiRequest<Product[]>("/products/low-stock/"),

  groups: (params: { search?: string; page?: number; page_size?: number } = {}) =>
    apiRequest<Paginated<ProductGroup>>("/product-groups/", {
      query: { search: params.search, page: params.page, page_size: params.page_size },
    }),

  createGroup: (payload: ProductGroupPayload) =>
    apiRequest<ProductGroup>("/product-groups/", { method: "POST", body: payload }),

  updateGroup: (id: number, payload: Partial<ProductGroupPayload>) =>
    apiRequest<ProductGroup>(`/product-groups/${id}/`, { method: "PATCH", body: payload }),

  laboratories: (params: { search?: string; page_size?: number } = {}) =>
    apiRequest<Paginated<Laboratory>>("/laboratories/", {
      query: { search: params.search, page_size: params.page_size },
    }),

  categories: (params: { search?: string; page_size?: number } = {}) =>
    apiRequest<Paginated<Category>>("/categories/", {
      query: { search: params.search, page_size: params.page_size },
    }),

  ingredients: (params: { search?: string; page_size?: number } = {}) =>
    apiRequest<Paginated<ActiveIngredient>>("/active-ingredients/", {
      query: { search: params.search, page_size: params.page_size },
    }),

  /** Conversiones de presentacion (caja -> blister -> unidad). */
  unitConversions: (params: { source?: number; group?: number } = {}) =>
    apiRequest<Paginated<UnitConversion>>("/unit-conversions/", {
      query: { source: params.source, group: params.group },
    }),
};
