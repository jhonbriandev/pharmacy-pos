/**
 * Cliente HTTP de la API.
 *
 * Tres decisiones que conviene entender antes de tocar este archivo:
 *
 * 1. **CSRF explicito.** La sesion viaja en una cookie HttpOnly, y Django exige
 *    el token CSRF en cada escritura. Se lee de la cookie y se envia en
 *    `X-CSRFToken`; nunca se guarda en `localStorage`.
 * 2. **Errores uniformes.** El backend responde siempre
 *    `{ error: { code, message, details } }`. Aqui se convierte en un
 *    `ApiError` con `code` estable: la interfaz decide por codigo, no por texto.
 * 3. **Cero calculos de negocio.** Este cliente no suma totales ni ajusta
 *    precios; solo transporta. El servidor es la autoridad.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/+$/, "");

export type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** La peticion era valida pero el estado del negocio no permitia completarla. */
  get isConflict(): boolean {
    return this.status === 409;
  }

  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }

  get isValidationError(): boolean {
    return this.status === 400;
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfInFlight: Promise<void> | null = null;

/**
 * Garantiza que exista la cookie `csrftoken`.
 *
 * Se llama al arrancar la aplicacion y antes de la primera escritura. No se
 * cachea el token: Django lo rota al iniciar sesion, asi que siempre se lee la
 * cookie vigente.
 */
export function ensureCsrf(): Promise<void> {
  if (readCookie("csrftoken")) return Promise.resolve();
  if (!csrfInFlight) {
    csrfInFlight = fetch(`${BASE_URL}/auth/csrf/`, {
      credentials: "include",
      headers: { Accept: "application/json" },
    })
      .then(() => undefined)
      .finally(() => {
        csrfInFlight = null;
      });
  }
  return csrfInFlight;
}

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  signal?: AbortSignal;
  query?: Record<string, string | number | boolean | null | undefined>;
  /** Permite leer una respuesta que no es JSON (por ejemplo un CSV). */
  raw?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  if (!query) return url;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const queryString = params.toString();
  return queryString ? `${url}?${queryString}` : url;
}

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
}

async function toApiError(response: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope | null;
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    envelope = null;
  }

  const code = envelope?.error?.code ?? fallbackCode(response.status);
  const message = envelope?.error?.message ?? fallbackMessage(response.status);
  return new ApiError(response.status, code, message, envelope?.error?.details ?? null);
}

function fallbackCode(status: number): string {
  switch (status) {
    case 400:
      return "validation_error";
    case 401:
      return "not_authenticated";
    case 403:
      return "permission_denied";
    case 404:
      return "not_found";
    case 409:
      return "conflict";
    default:
      return status >= 500 ? "server_error" : "error";
  }
}

function fallbackMessage(status: number): string {
  switch (status) {
    case 400:
      return "Revisa los datos ingresados.";
    case 401:
      return "Tu sesion expiro. Vuelve a iniciar sesion.";
    case 403:
      return "No tienes permisos para esta accion.";
    case 404:
      return "No encontramos lo que buscabas.";
    case 409:
      return "La operacion no se pudo completar con los datos actuales.";
    default:
      return status >= 500
        ? "Ocurrio un error en el servidor. Intenta de nuevo."
        : "No se pudo completar la operacion.";
  }
}

const UNSAFE_METHODS: HttpMethod[] = ["POST", "PATCH", "PUT", "DELETE"];

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, query, raw = false } = options;

  if (UNSAFE_METHODS.includes(method)) {
    await ensureCsrf();
  }

  const headers: Record<string, string> = { Accept: raw ? "*/*" : "application/json" };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (UNSAFE_METHODS.includes(method)) {
    const token = readCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      credentials: "include",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      0,
      "network_error",
      "No se pudo conectar con el servidor. Revisa tu conexion.",
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (raw) {
    return (await response.text()) as T;
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  if (!contentType.includes("application/json")) {
    return (await response.text()) as T;
  }

  return (await response.json()) as T;
}

/** Extrae un mensaje legible de cualquier error, para mostrarlo en la UI. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return error.message;

    const details = error.details;
    if (details && typeof details === "object") {
      const firstValue = Object.values(details as Record<string, unknown>)[0];
      if (Array.isArray(firstValue) && firstValue.length > 0) {
        return String(firstValue[0]);
      }
      if (typeof firstValue === "string") return firstValue;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Ocurrio un error inesperado.";
}
