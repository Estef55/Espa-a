// Adaptaciones accesibles (backend: /api/v1/adaptations, solo docente). Los errores 501 significan
// «capacidad no instalada/configurada»; la interfaz debe mostrarlo, no simular un resultado.
import { request } from "./http.ts";
import type { CapabilitiesResponse } from "../lib/resources.ts";

export type AdaptationEnvelope<T = unknown> = {
  material_id: string; adaptation: string; result: T; review_required: boolean; generated_at: string;
  requires_server?: boolean; requires_internet?: boolean;
};

export const getCapabilities = () => request<CapabilitiesResponse>("/api/v1/adaptations/capabilities");
export const buildVisual = (id: string, kind: "outline" | "concept_map", options: Record<string, number> = {}) =>
  request<AdaptationEnvelope>(`/api/v1/adaptations/materials/${encodeURIComponent(id)}/visual`, { method: "POST", body: { kind, options } });
export const buildAccessible = (id: string, format: "plain" | "html" | "braille" | "bundle", language = "es") =>
  request<AdaptationEnvelope>(`/api/v1/adaptations/materials/${encodeURIComponent(id)}/accessible`, { method: "POST", body: { format, language } });
export const buildAudioScript = (id: string, language = "es", max_chars = 400) =>
  request<AdaptationEnvelope>(`/api/v1/adaptations/materials/${encodeURIComponent(id)}/audio-script`, { method: "POST", body: { language, max_chars } });
export const buildAudio = (id: string, language = "es") =>
  request<AdaptationEnvelope>(`/api/v1/adaptations/materials/${encodeURIComponent(id)}/audio`, { method: "POST", body: { language }, timeoutMs: 180000 });
export const translateMaterial = (id: string, target: string, source = "es") =>
  request<AdaptationEnvelope>(`/api/v1/adaptations/materials/${encodeURIComponent(id)}/translate`, { method: "POST", body: { target, source }, timeoutMs: 180000 });
export const inspectImage = (image_base64: string) =>
  request<Record<string, unknown>>("/api/v1/adaptations/images/inspect", { method: "POST", body: { image_base64 } });
export const describeImage = (image_base64: string, language = "es") =>
  request<AdaptationEnvelope>("/api/v1/adaptations/images/describe", { method: "POST", body: { image_base64, language } });
export const subtitlesToText = (content: string) =>
  request<Record<string, unknown>>("/api/v1/adaptations/subtitles", { method: "POST", body: { content } });
