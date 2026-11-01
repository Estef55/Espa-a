// Tipos de los contratos reales del backend (confirmados en backend/app y ai/).
export type Role = "student" | "teacher" | "admin";

export type Assignment = {
  id: string; title: string; instructions: string; classroom_id?: string | null;
  due_at?: string | null; created_by?: string; status: "draft" | "published" | "closed" | string;
  version: number; created_at?: string; updated_at?: string;
};
export type Submission = {
  id: string; assignment_id: string; student_id: string; answer: string;
  status: "submitted" | "reviewed" | "returned" | string; server_version: number;
  client_updated_at?: string | null; updated_at?: string; created_at?: string;
};
export type LibraryMaterial = {
  id: string; title: string; description: string; resource_url: string; mime_type: string;
  status: "draft" | "published" | string; created_by?: string; created_at?: string;
};
export type UploadedMaterial = {
  id: string; filename: string; content_type: string; size: number; sha256: string;
  extracted_at: string | null; created_at: string;
};
export type ExtractionResult = { material_id: string; text: string; characters: number; ocr_used: boolean };
export type AdaptationKind = "summary" | "easy_read" | "quiz";
export type QuizQuestion = {
  id: number; type: string; question: string; reference_fragment: string; topic_hint: string;
  answer_key: string | null; teacher_review_required: boolean;
};
export type AdaptationResult = {
  material_id: string; adaptation: AdaptationKind; result: string | QuizQuestion[];
  review_required: boolean; generated_at: string;
};
export type DocumentSummary = {
  id: string; title: string; source_material_id: string | null; current_version: number;
  archived: boolean; created_at: string; updated_at: string;
};
export type DocumentFull = DocumentSummary & { content: string };
export type DocumentVersionInfo = {
  version: number; author_id: string; reason: string; restored_from: number | null; created_at: string; size: number;
};
export type DocumentVersionFull = Omit<DocumentVersionInfo, "size"> & { content: string };
export type PreferenceKey = "education_level" | "complexity" | "length" | "tone" | "format" | "language";
export type Preferences = Record<PreferenceKey, string | null>;
export type PreferencesResponse = {
  preferences: Preferences; is_default: boolean; updated_at: string | null; allowed_values: Record<PreferenceKey, string[]>;
};
export type ChatMessage = { role: "user" | "assistant" | "system"; content: string; created_at?: string };
export type ChatReply = {
  conversation_id: string; answer: string; generated_by_model: boolean; provider: string; model: string;
  document_context: { document_id: string; title: string; version: number; truncated: boolean } | null;
  preferences_applied: Preferences; notice: string;
};
export type Conversation = { id: string; document_id: string | null; created_at: string; messages: ChatMessage[] };
export type AiStatus = {
  ai_provider_configured: boolean; document_processor_connected: boolean; learning_data_source_connected: boolean;
};
export type ReportCriteria = {
  pass_threshold_pct?: number; topic?: string | null; group?: string | null; date_from?: string | null;
  date_to?: string | null; include_ai_interpretation?: boolean;
};
export type ReportListItem = { id: string; created_at: string; status: string; criteria: ReportCriteria };
export type Report = {
  id: string; created_at: string; status: "ok" | "insufficient_data" | string; criteria: ReportCriteria;
  data_summary?: { source: string; records_received: number; records_used: number; records_invalid: number };
  metrics?: { measured?: Record<string, unknown>; calculated?: Record<string, unknown> } | null;
  observations?: { id: string; kind: string; text: string }[];
  recommendations?: { id: string; based_on: string[]; text: string }[];
  missing?: string[]; limitations?: string[]; legend?: Record<string, string>;
  ai_interpretation?: { status: string; text?: string; reason?: string; model?: string; provider?: string } | null;
};
export type SyncPull = { assignments: Assignment[]; submissions: Submission[]; server_time: string };
export type SyncServerStatus = { server: string; accepted_last_24h: number; last_received_at: string | null; actor_id: string };
export type Health = { status: string; project: string; database: string; engine: string };
