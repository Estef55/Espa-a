// Documentos editables con historial (backend: /api/v1/documents, solo docente).
import { request } from "./http.ts";
import type { DocumentFull, DocumentSummary, DocumentVersionFull, DocumentVersionInfo } from "../lib/types.ts";

const base = "/api/v1/documents";
export const listDocuments = (includeArchived = false) => request<DocumentSummary[]>(base, { query: { include_archived: includeArchived ? "true" : undefined } });
export const getDocument = (id: string) => request<DocumentFull>(`${base}/${encodeURIComponent(id)}`);
export const createDocument = (data: { title: string; content: string; source_material_id?: string }) => request<DocumentFull>(base, { method: "POST", body: data });
export const importDocument = (materialId: string) => request<DocumentFull>(`${base}/import`, { method: "POST", body: { material_id: materialId } });
export const saveDocument = (id: string, content: string, expectedVersion: number, reason?: string) =>
  request<DocumentFull>(`${base}/${encodeURIComponent(id)}`, { method: "PUT", body: { content, expected_version: expectedVersion, ...(reason ? { reason } : {}) } });
export const listVersions = (id: string) => request<DocumentVersionInfo[]>(`${base}/${encodeURIComponent(id)}/versions`);
export const getVersion = (id: string, version: number) => request<DocumentVersionFull>(`${base}/${encodeURIComponent(id)}/versions/${version}`);
export const restoreVersion = (id: string, version: number, expectedVersion: number, reason?: string) =>
  request<DocumentFull>(`${base}/${encodeURIComponent(id)}/restore`, { method: "POST", body: { version, expected_version: expectedVersion, ...(reason ? { reason } : {}) } });
export const archiveDocument = (id: string) => request<DocumentSummary>(`${base}/${encodeURIComponent(id)}/archive`, { method: "POST" });
