// Tipos de la API de materiales y adaptaciones (integrante 2). Reflejan las respuestas reales de /api/v1/materials.
import type { AdaptationKind, QuizQuestion } from "./types.ts";

export type MaterialStatus = "uploaded" | "extracted" | "no_text" | "failed";
export type ReviewStatus = "pending" | "approved";
export type AdaptationStatus = "complete" | "partial";

export type MaterialInfo = {
  id: string; filename: string; content_type: string; size: number; sha256: string;
  created_at: string; extracted_at: string | null;
  status: MaterialStatus; method: string | null; attempts: number;
  error: { code: string; message: string } | null;
  page_count: number | null; image_count: number | null; warnings: string[];
  is_demo: boolean; adaptation_count: number;
};
export type TextBlock = { type: "heading" | "paragraph" | "list" | "table_like" | "notice"; text: string; page?: number | null };
export type OrganizedText = {
  material_id: string;
  organized: { clean_text: string; blocks: TextBlock[]; stats?: Record<string, number>; warnings?: string[] };
};
export type AdaptationLink = { target_type: "document" | "assignment"; target_id: string; created_at?: string };
export type AdaptationRecord = {
  id: string | null; material_id: string; adaptation: AdaptationKind; label?: string;
  status: AdaptationStatus | "empty"; persisted?: boolean;
  result: string | QuizQuestion[] | Record<string, unknown>; text: string;
  warnings: string[]; source_origin?: "extracted" | "edited";
  review_status?: ReviewStatus; review_required: boolean; reviewed_at?: string | null;
  created_at?: string; generated_at?: string; links?: AdaptationLink[];
};
export type Feature = { available: boolean; reason: string | null; needs_internet: boolean; limits?: string; languages?: string; engine?: string | null };
export type Capabilities = { formats: string[]; max_upload_bytes: number; features: Record<string, Feature> };
export type TextResult = { material_id: string; text: string; characters: number; ocr_used: boolean; status: MaterialStatus; method: string | null; page_count: number | null; warnings: string[] };
export type ExportFormat = "html" | "txt";
