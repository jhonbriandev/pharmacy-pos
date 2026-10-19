/** Endpoints de autenticacion y usuarios. */

import { apiRequest } from "../client";
import type { Me, Paginated, Role, RoleOption, User } from "../types";

export interface LoginPayload {
  username: string;
  password: string;
}

export interface UserListParams {
  search?: string;
  role?: Role | "";
  is_active?: boolean;
  page?: number;
}

export interface UserCreatePayload {
  username: string;
  first_name: string;
  last_name: string;
  email?: string;
  role: Role;
  password: string;
  must_change_password?: boolean;
}

export interface UserUpdatePayload {
  first_name?: string;
  last_name?: string;
  email?: string;
}

export const authApi = {
  login: (payload: LoginPayload) => apiRequest<User>("/auth/login/", { method: "POST", body: payload }),

  logout: () => apiRequest<void>("/auth/logout/", { method: "POST" }),

  me: () => apiRequest<Me>("/auth/me/"),

  changePassword: (currentPassword: string, newPassword: string) =>
    apiRequest<{ detail: string }>("/auth/password/change/", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    }),

  roles: () => apiRequest<RoleOption[]>("/roles/"),
};

export const usersApi = {
  list: (params: UserListParams = {}) =>
    apiRequest<Paginated<User>>("/users/", {
      query: {
        search: params.search,
        role: params.role,
        is_active: params.is_active,
        page: params.page,
      },
    }),

  create: (payload: UserCreatePayload) =>
    apiRequest<User>("/users/", { method: "POST", body: payload }),

  update: (id: number, payload: UserUpdatePayload) =>
    apiRequest<User>(`/users/${id}/`, { method: "PATCH", body: payload }),

  deactivate: (id: number) => apiRequest<User>(`/users/${id}/deactivate/`, { method: "POST" }),

  setRole: (id: number, role: Role) =>
    apiRequest<User>(`/users/${id}/role/`, { method: "POST", body: { role } }),

  resetPassword: (id: number, newPassword: string) =>
    apiRequest<{ detail: string }>(`/users/${id}/reset-password/`, {
      method: "POST",
      body: { new_password: newPassword },
    }),
};
