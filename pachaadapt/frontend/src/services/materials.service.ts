// Carga, extracción y adaptación de PDF/TXT (backend: /api/v1/materials, solo docente).
import { request, requestBlob } from "./http.ts";
import type { AdaptationKind, ExtractionResult, UploadedMaterial } from "../lib/types.ts";
import type { AdaptationRecord, Capabilities, ExportFormat, MaterialInfo, OrganizedText } from "../lib/materials.types.ts";

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
  return request<AdaptationRecord>(`/api/v1/materials/${encodeURIComponent(id)}/adapt`, {
    method: "POST", body: { adaptation, ...(text !== undefined ? { text } : {}), options: rest }, timeoutMs: 180000,
  });
}

// ---- Integrante 2: lista, estado, texto organizado, adaptaciones persistidas, original y exportaciones ----

const base = (id: string) => `/api/v1/materials/${encodeURIComponent(id)}`;
export function listMaterials() { return request<MaterialInfo[]>("/api/v1/materials"); }
export function getMaterialInfo(id: string) { return request<MaterialInfo>(base(id)); }
export function getCapabilities() { return request<Capabilities>("/api/v1/materials/capabilities"); }
export function getMaterialText(id: string) { return request<OrganizedText>(`${base(id)}/text`); }
export function listAdaptations(id: string) { return request<AdaptationRecord[]>(`${base(id)}/adaptations`); }
export function reviewAdaptation(id: string, adaptationId: string, approved: boolean) {
  return request<AdaptationRecord>(`${base(id)}/adaptations/${encodeURIComponent(adaptationId)}/review`, { method: "POST", body: { approved } });
}
export function linkAdaptation(id: string, adaptationId: string, targetType: "document" | "assignment", targetId: string) {
  return request<AdaptationRecord>(`${base(id)}/adaptations/${encodeURIComponent(adaptationId)}/links`, { method: "POST", body: { target_type: targetType, target_id: targetId } });
}
export function downloadOriginal(id: string) { return requestBlob(`${base(id)}/original`); }
export function exportAdaptation(id: string, adaptationId: string, format: ExportFormat) {
  return requestBlob(`${base(id)}/adaptations/${encodeURIComponent(adaptationId)}/export?format=${format}`);
}
export function downloadAudio(id: string, adaptationId: string) { return requestBlob(`${base(id)}/adaptations/${encodeURIComponent(adaptationId)}/audio`); }
