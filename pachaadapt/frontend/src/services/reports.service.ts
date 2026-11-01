// Informes de resultados de aprendizaje (backend: /api/v1/reports, solo docente).
import { request } from "./http.ts";
import type { Report, ReportCriteria, ReportListItem } from "../lib/types.ts";

export const listReports = () => request<ReportListItem[]>("/api/v1/reports");
export const getReport = (id: string) => request<Report>(`/api/v1/reports/${encodeURIComponent(id)}`);
export const getReportMarkdown = (id: string) => request<string>(`/api/v1/reports/${encodeURIComponent(id)}/markdown`, { raw: true });
/** El backend rechaza claves desconocidas: se descartan los campos vacíos. */
export function createReport(criteria: ReportCriteria) {
  const body = Object.fromEntries(Object.entries(criteria).filter(([, v]) => v !== undefined && v !== null && v !== ""));
  return request<Report>("/api/v1/reports", { method: "POST", body, timeoutMs: 90000 });
}
