// Carga, extracción y adaptación de PDF/TXT (backend: /api/v1/materials, solo docente).
import { request } from "./http.ts";
import type { AdaptationKind, AdaptationResult, ExtractionResult, UploadedMaterial } from "../lib/types.ts";

export const MATERIAL_ID = /^[a-f0-9]{32}$/;
export const ALLOWED_EXTENSIONS = [".pdf", ".txt"];
export const DEFAULT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024; // valor por defecto del servidor; el servidor es quien valida

/** Validación previa en el navegador; el servidor vuelve a validar. Devuelve un mensaje o null. */
export function validateUpload(file: { name: string; size: number }): string | null {
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!ALLOWED_EXTENSIONS.includes(ext)) return "Formato no admitido. Se aceptan archivos PDF y TXT.";
  if (file.size === 0) return "El archivo está vacío.";
  if (file.size > DEFAULT_MAX_UPLOAD_BYTES) return "El archivo supera 25 MB, el límite habitual del servidor.";
  return null;
}
export function uploadMaterial(file: File) {
  const form = new FormData(); form.append("file", file, file.name);
  return request<UploadedMaterial>("/api/v1/materials", { method: "POST", form, timeoutMs: 120000 });
}
export function getUploadedMaterial(id: string) {
  return request<UploadedMaterial>(`/api/v1/materials/${encodeURIComponent(id)}`);
}
export function extractMaterial(id: string, ocr: boolean) {
  return request<ExtractionResult>(`/api/v1/materials/${encodeURIComponent(id)}/extract`, { method: "POST", body: { ocr }, timeoutMs: 180000 });
}
export function adaptMaterial(id: string, adaptation: AdaptationKind, options: { text?: string; max_sentences?: number; max_words?: number; count?: number; ocr?: boolean } = {}) {
  const { text, ...rest } = options;
  return request<AdaptationResult>(`/api/v1/materials/${encodeURIComponent(id)}/adapt`, {
    method: "POST", body: { adaptation, ...(text !== undefined ? { text } : {}), options: rest }, timeoutMs: 180000,
  });
}
