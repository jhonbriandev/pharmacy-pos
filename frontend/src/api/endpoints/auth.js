/** Endpoints de autenticacion y usuarios. */

import { apiRequest } from "../client";
export const authApi = {
  login: (payload) =>
    apiRequest("/auth/login/", {
      method: "POST",
      body: payload,
    }),
  logout: () =>
    apiRequest("/auth/logout/", {
      method: "POST",
    }),
  me: () => apiRequest("/auth/me/"),
  changePassword: (currentPassword, newPassword) =>
    apiRequest("/auth/password/change/", {
      method: "POST",
      body: {
        current_password: currentPassword,
        new_password: newPassword,
      },
    }),
  roles: () => apiRequest("/roles/"),
};
export const usersApi = {
  list: (params = {}) =>
    apiRequest("/users/", {
      query: {
        search: params.search,
        role: params.role,
        is_active: params.is_active,
        page: params.page,
      },
    }),
  create: (payload) =>
    apiRequest("/users/", {
      method: "POST",
      body: payload,
    }),
  update: (id, payload) =>
    apiRequest(`/users/${id}/`, {
      method: "PATCH",
      body: payload,
    }),
  deactivate: (id) =>
    apiRequest(`/users/${id}/deactivate/`, {
      method: "POST",
    }),
  setRole: (id, role) =>
    apiRequest(`/users/${id}/role/`, {
      method: "POST",
      body: {
        role,
      },
    }),
  resetPassword: (id, newPassword) =>
    apiRequest(`/users/${id}/reset-password/`, {
      method: "POST",
      body: {
        new_password: newPassword,
      },
    }),
};
