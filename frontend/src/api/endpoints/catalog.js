/** Endpoints del catalogo de productos. */

import { apiRequest } from "../client";
export const catalogApi = {
  products: (params = {}) =>
    apiRequest("/products/", {
      query: {
        search: params.search,
        is_active: params.is_active,
        presentation: params.presentation,
        group: params.group,
        page: params.page,
      },
    }),
  product: (id) => apiRequest(`/products/${id}/`),
  createProduct: (payload) =>
    apiRequest("/products/", {
      method: "POST",
      body: payload,
    }),
  updateProduct: (id, payload) =>
    apiRequest(`/products/${id}/`, {
      method: "PATCH",
      body: payload,
    }),
  productLots: (id) => apiRequest(`/products/${id}/lots/`),
  /** Busqueda por texto: devuelve hasta 20 productos activos. */
  search: (query) =>
    apiRequest("/products/lookup/", {
      query: {
        q: query,
      },
    }),
  /** Lectura de codigo de barras: devuelve uno o falla con 404. */
  byBarcode: (barcode) =>
    apiRequest("/products/lookup/", {
      query: {
        barcode,
      },
    }),
  lowStock: () => apiRequest("/products/low-stock/"),
  groups: (params = {}) =>
    apiRequest("/product-groups/", {
      query: {
        search: params.search,
        page: params.page,
        page_size: params.page_size,
      },
    }),
  createGroup: (payload) =>
    apiRequest("/product-groups/", {
      method: "POST",
      body: payload,
    }),
  updateGroup: (id, payload) =>
    apiRequest(`/product-groups/${id}/`, {
      method: "PATCH",
      body: payload,
    }),
  laboratories: (params = {}) =>
    apiRequest("/laboratories/", {
      query: {
        search: params.search,
        page_size: params.page_size,
      },
    }),
  categories: (params = {}) =>
    apiRequest("/categories/", {
      query: {
        search: params.search,
        page_size: params.page_size,
      },
    }),
  ingredients: (params = {}) =>
    apiRequest("/active-ingredients/", {
      query: {
        search: params.search,
        page_size: params.page_size,
      },
    }),
  /** Conversiones de presentacion (caja -> blister -> unidad). */
  unitConversions: (params = {}) =>
    apiRequest("/unit-conversions/", {
      query: {
        source: params.source,
        group: params.group,
      },
    }),
};
