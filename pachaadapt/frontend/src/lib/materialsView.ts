// Textos y reglas de presentación de materiales/adaptaciones. Funciones puras, sin red ni DOM (se prueban con node --test).
import type { AdaptationKind } from "./types.ts";
import type { AdaptationRecord, Capabilities, Feature, MaterialInfo, MaterialStatus } from "./materials.types.ts";

export const KINDS: AdaptationKind[] = ["summary", "easy_read", "outline", "quiz", "image_notes", "audio"];
export const KIND_LABEL: Record<AdaptationKind, string> = {
  summary: "Resumen", easy_read: "Lectura fácil", outline: "Esquema del contenido", quiz: "Preguntas de comprensión",
  image_notes: "Notas de imágenes", audio: "Audio",
};
/** Qué hace realmente cada adaptación (para no prometer más de lo que ofrece). */
export const KIND_HELP: Record<AdaptationKind, string> = {
  summary: "Selecciona las oraciones más importantes del propio texto. No redacta contenido nuevo.",
  easy_read: "Parte las oraciones largas y quita paréntesis y relleno. No cambia el vocabulario ni explica conceptos.",
  outline: "Lista de títulos y puntos del documento en el mismo orden. Es una lista, no un mapa conceptual.",
  quiz: "Preguntas abiertas basadas en fragmentos del texto. No incluye respuestas correctas: las define el docente.",
  image_notes: "Pies de figura y texto dentro de las imágenes (con OCR). No describe lo que muestra la imagen.",
  audio: "Lee el texto con un motor de voz instalado en el servidor. Solo existe si el servidor lo tiene.",
};
export const STATUS_TEXT: Record<MaterialStatus, string> = {
  uploaded: "Subido, sin extraer", extracted: "Texto extraído", no_text: "Sin texto legible", failed: "Falló la extracción",
};
const FEATURE_KEY: Record<AdaptationKind, string> = { summary: "summary", easy_read: "easy_read", outline: "outline", quiz: "quiz", image_notes: "image_notes", audio: "audio" };

export type Availability = { available: boolean; reason: string; needsInternet: boolean };
/** Disponibilidad según lo que informa el servidor. Sin información del servidor se considera NO disponible. */
export function kindAvailability(caps: Capabilities | null | undefined, kind: AdaptationKind): Availability {
  const f: Feature | undefined = caps?.features?.[FEATURE_KEY[kind]];
  if (!f) return { available: false, reason: "No se pudo consultar qué ofrece el servidor.", needsInternet: false };
  return { available: f.available, reason: f.available ? "" : (f.reason ?? "No disponible en este servidor."), needsInternet: f.needs_internet };
}
/** Capacidades que el proyecto describe pero que NO existen (nunca se muestran con botón activo). */
export const NOT_IMPLEMENTED = ["Traducción automática", "Adaptación al quechua", "Braille desde esta pantalla (existe en el servidor, sin interfaz todavía)", "Transcripción de audio o video", "Descripción visual de imágenes con IA"];

export type Badge = { text: string; tone: "ok" | "warn" | "info" };
export function adaptationBadge(a: Pick<AdaptationRecord, "status" | "review_status">): Badge {
  const reviewed = a.review_status === "approved";
  if (a.status === "partial") return { text: reviewed ? "Parcial · revisada" : "Parcial · sin revisar", tone: "warn" };
  return reviewed ? { text: "Completa · revisada por el docente", tone: "ok" } : { text: "Completa · pendiente de revisión", tone: "info" };
}
export function materialStatusTone(s: MaterialStatus): "ok" | "warn" | "info" { return s === "extracted" ? "ok" : s === "uploaded" ? "info" : "warn"; }

/** Nombre de adaptación por tipo, en orden, para enlazarla a su original. */
export function groupByKind(list: AdaptationRecord[]): Array<{ kind: AdaptationKind; items: AdaptationRecord[] }> {
  return KINDS.map(kind => ({ kind, items: list.filter(a => a.adaptation === kind) })).filter(g => g.items.length);
}

export type OfflineLevel = "full" | "partial" | "none";
/** Qué parte de un material quedó guardada en este dispositivo. */
export function resourceOffline(s: { detail: boolean; original: boolean }): { level: OfflineLevel; text: string } {
  if (s.detail && s.original) return { level: "full", text: "Disponible sin conexión: datos, adaptaciones y archivo original guardados en este dispositivo." };
  if (s.detail) return { level: "partial", text: "Sin conexión solo se pueden leer los datos y las adaptaciones guardadas; el archivo original no está descargado." };
  if (s.original) return { level: "partial", text: "El archivo original está guardado, pero no sus adaptaciones." };
  return { level: "none", text: "Requiere conexión: nada de este material está guardado en este dispositivo." };
}
export function offlineSummary(rows: Array<{ level: OfflineLevel }>): string {
  const full = rows.filter(r => r.level === "full").length, part = rows.filter(r => r.level === "partial").length;
  if (!rows.length) return "No hay materiales en la lista.";
  return `${full} de ${rows.length} materiales disponibles sin conexión${part ? `, ${part} parcialmente` : ""}.`;
}
/** Qué recursos necesitan servicios de Internet (ninguno de los locales) frente a conexión con el servidor. */
export function connectionNeeds(caps: Capabilities | null | undefined): Array<{ label: string; ok: boolean; needsInternet: boolean; reason: string }> {
  const rows = KINDS.map(k => ({ label: KIND_LABEL[k], ...(({ available, needsInternet, reason }) => ({ ok: available, needsInternet, reason }))(kindAvailability(caps, k)) }));
  const ocr = caps?.features?.ocr;
  rows.push({ label: "Lectura de PDF escaneados (OCR)", ok: !!ocr?.available, needsInternet: !!ocr?.needs_internet, reason: ocr?.available ? "" : (ocr?.reason ?? "No se pudo consultar.") });
  return rows;
}
export function canGenerate(material: Pick<MaterialInfo, "status">): string | null {
  if (material.status === "extracted") return null;
  if (material.status === "no_text") return "El documento no tiene texto legible. Prueba la extracción con OCR si el servidor lo ofrece.";
  if (material.status === "failed") return "La extracción falló. Corrige el problema y vuelve a intentarla.";
  return "Primero extrae el texto del material.";
}
