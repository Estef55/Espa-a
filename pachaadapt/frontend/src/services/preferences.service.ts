// Preferencias del docente (backend: /api/v1/preferences, solo docente).
import { request } from "./http.ts";
import type { Preferences, PreferencesResponse } from "../lib/types.ts";

export const getPreferences = () => request<PreferencesResponse>("/api/v1/preferences");
/** El backend rechaza claves desconocidas (extra="forbid"): solo se envían las modificadas. */
export const updatePreferences = (changes: Partial<Preferences>) => request<PreferencesResponse>("/api/v1/preferences", { method: "PUT", body: changes });
/** Elimina preferencias personalizadas del perfil autenticado y vuelve a valores por defecto. */
export const deletePreferences = () => request<PreferencesResponse>("/api/v1/preferences", { method: "DELETE" });
export const getAdaptationParams = () => request<{ proposed_params: Record<string, string> }>("/api/v1/preferences/adaptation-params");
