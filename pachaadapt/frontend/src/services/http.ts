// Cliente HTTP común: cabeceras de identidad de demostración y normalización de errores.
import type { Role } from "../lib/types.ts";

const env = (import.meta as unknown as { env?: { VITE_API_URL?: string } }).env;
export const API: string = env?.VITE_API_URL ?? "";

export const ID_PATTERN = /^[A-Za-z0-9_.@-]{1,64}$/; // mismo patrón que backend/app/core/identity.py
let actor: { id: string; role: Role } = { id: "demo-student", role: "student" };
export function setActor(id: string, role: Role) { actor = { id, role }; }
export function getActor() { return actor; }

/** Cabeceras de identidad (solo desarrollo: no son autenticación real). */
export function identityHeaders(): Record<string, string> {
  return { "X-User-Id": actor.id, "X-Role": actor.role };
}
export function apiHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { "Content-Type": "application/json", ...identityHeaders(), ...extra };
}

export type ApiErrorKind = "network" | "auth" | "forbidden" | "not_found" | "conflict" | "validation"
  | "unavailable" | "not_implemented" | "too_large" | "timeout" | "server" | "unknown";

export class ApiError extends Error {
  status: number; code: string; kind: ApiErrorKind; extra: Record<string, unknown>;
  constructor(message: string, status: number, code: string, kind: ApiErrorKind, extra: Record<string, unknown> = {}) {
    super(message); this.name = "ApiError"; this.status = status; this.code = code; this.kind = kind; this.extra = extra;
  }
}

const KIND_BY_STATUS: Record<number, ApiErrorKind> = {
  401: "auth", 403: "forbidden", 404: "not_found", 409: "conflict", 413: "too_large", 422: "validation",
  501: "not_implemented", 502: "server", 503: "unavailable", 504: "timeout",
};
const FALLBACK_MESSAGE: Record<ApiErrorKind, string> = {
  network: "No se pudo contactar con el backend. Comprueba que esté iniciado (python scripts/start_server.py) y vuelve a intentarlo.",
  auth: "El servidor no reconoce la identidad del perfil actual.",
  forbidden: "El perfil actual no tiene permiso para esta función.",
  not_found: "No se encontró el recurso solicitado.",
  conflict: "El dato cambió en el servidor mientras lo editabas. Recarga y vuelve a intentarlo.",
  validation: "Los datos enviados no son válidos.",
  unavailable: "Esta función no está disponible en el servidor en este momento.",
  not_implemented: "El servidor no tiene disponible esta capacidad (por ejemplo, OCR sin sus dependencias).",
  too_large: "El archivo supera el tamaño máximo permitido.",
  timeout: "El servidor tardó demasiado en responder.",
  server: "El servidor devolvió un error.", unknown: "Ocurrió un error inesperado.",
};

type Detail = string | { code?: string; message?: string; [k: string]: unknown } | Array<{ loc?: unknown[]; msg?: string }>;

/** Error de red: el backend no responde (apagado, puerto equivocado o sin conexión). */
export const networkError = () => new ApiError(FALLBACK_MESSAGE.network, 0, "network", "network");

/** Convierte una respuesta no exitosa en ApiError con mensaje en español. */
export async function toApiError(response: Response): Promise<ApiError> {
  const kind = KIND_BY_STATUS[response.status] ?? (response.status >= 500 ? "server" : "unknown");
  let message = ""; let code: string = kind; let extra: Record<string, unknown> = {};
  const raw = await response.text().catch(() => "");
  // El proxy de Vite responde 500/502/504 SIN cuerpo cuando no logra conectar con el backend: se trata como fallo de red.
  if ([500, 502, 504].includes(response.status) && raw.trim() === "") return networkError();
  try {
    const detail = (JSON.parse(raw) as { detail?: Detail }).detail;
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail)) {
      message = detail.map(d => `${(d.loc ?? []).filter(p => p !== "body").join(".")}: ${d.msg ?? "inválido"}`).join("; ");
    } else if (detail && typeof detail === "object") {
      const { code: c, message: m, ...rest } = detail;
      if (typeof c === "string") code = c; if (typeof m === "string") message = m; extra = rest;
    }
  } catch { /* cuerpo no JSON: se usa el mensaje genérico */ }
  if (kind === "unavailable" && code === "auth_not_configured") {
    message = "El servidor no tiene activada la identidad de demostración (PACHAADAPT_I3_DEV_AUTH=1). Inícialo con scripts/start_server.py.";
  }
  return new ApiError(message || FALLBACK_MESSAGE[kind], response.status, code, kind, extra);
}

export type RequestOptions = { method?: string; body?: unknown; form?: FormData; query?: Record<string, string | number | boolean | undefined>; timeoutMs?: number; raw?: boolean };

/** Petición al backend. Lanza ApiError; los fallos de red se normalizan a kind "network". */
export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API}${path}`, typeof window === "undefined" ? "http://localhost" : window.location.origin);
  for (const [k, v] of Object.entries(opts.query ?? {})) if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  const headers = opts.form ? identityHeaders() : apiHeaders();
  let response: Response;
  try {
    response = await fetch(url, {
      method: opts.method ?? "GET", headers,
      body: opts.form ?? (opts.body === undefined ? undefined : JSON.stringify(opts.body)),
      signal: AbortSignal.timeout(opts.timeoutMs ?? 30000),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") throw new ApiError(FALLBACK_MESSAGE.timeout, 0, "timeout", "timeout");
    throw networkError();
  }
  if (!response.ok) throw await toApiError(response);
  if (opts.raw) return (await response.text()) as T;
  return (await response.json()) as T;
}

export function errorMessage(error: unknown, fallback = "Ocurrió un error inesperado."): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

/** Descarga binaria (original, audio, exportaciones). Mismos errores normalizados que `request`. */
export async function requestBlob(path: string, opts: { timeoutMs?: number } = {}): Promise<{ blob: Blob; filename: string | null }> {
  const url = new URL(`${API}${path}`, typeof window === "undefined" ? "http://localhost" : window.location.origin);
  let response: Response;
  try {
    response = await fetch(url, { headers: identityHeaders(), signal: AbortSignal.timeout(opts.timeoutMs ?? 120000) });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") throw new ApiError(FALLBACK_MESSAGE.timeout, 0, "timeout", "timeout");
    throw networkError();
  }
  if (!response.ok) throw await toApiError(response);
  const match = /filename="?([^";]+)"?/.exec(response.headers.get("Content-Disposition") ?? "");
  return { blob: await response.blob(), filename: match ? match[1] : null };
}
