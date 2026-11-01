// Exportación CSV de entregas, generada en el navegador (el backend no tiene endpoint de exportación).
import type {Submission} from "./types";
import {statusLabel} from "./format.ts";

/** Neutraliza fórmulas (=, +, -, @) que Excel ejecutaría al abrir el archivo. */
export function csvCell(value:unknown):string{
  let text=String(value??"");
  if(/^[=+\-@\t\r]/.test(text))text="'"+text;
  return `"${text.replaceAll('"','""')}"`;
}
export function buildSubmissionsCsv(submissions:Submission[],titleOf:(assignmentId:string)=>string|undefined):string{
  const rows=[["Estudiante","Actividad","Respuesta","Estado","Versión"],
    ...submissions.map(s=>[s.student_id,titleOf(s.assignment_id)??s.assignment_id,s.answer,statusLabel(s.status),String(s.server_version)])];
  return "\uFEFF"+rows.map(row=>row.map(csvCell).join(";")).join("\r\n");
}
export function downloadText(filename:string,text:string,type="text/csv;charset=utf-8"){
  const url=URL.createObjectURL(new Blob([text],{type}));
  const a=document.createElement("a");a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
