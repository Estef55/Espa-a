// Actividades, entregas y catálogo de materiales (backend: /assignments, /submissions, /material-library).
// Se conservan las exportaciones originales; los errores ahora son ApiError con mensajes en español.
import {loadAssignments,loadMaterials,type Cached} from "../offline/cache-manager";
import {queueSubmission} from "../offline/sync-queue";
import {apiHeaders,request,setActor,type ApiError} from "./http";
import type {Assignment,LibraryMaterial,Role,Submission} from "../lib/types";
export {reviewSubmission} from "./review.service";

export {apiHeaders,setActor};
export type {Role,ApiError};

export type AssignmentInput={title:string;instructions:string;status:"draft"|"published"|"closed";due_at?:string|null;classroom_id?:string|null};
export type LibraryMaterialInput={title:string;description:string;resource_url:string;mime_type:string;status?:"draft"|"published"};

/** Lista con indicación de si proviene de la copia local (modo sin conexión). */
export const fetchAssignments=()=>loadAssignments(apiHeaders()) as Promise<Cached<Assignment[]>>;
export const fetchMaterials=()=>loadMaterials(apiHeaders()) as Promise<Cached<LibraryMaterial[]>>;
export async function getAssignments(){return (await fetchAssignments()).data;}
export async function getMaterials(){return (await fetchMaterials()).data;}

export const createMaterial=(data:LibraryMaterialInput)=>request<LibraryMaterial>("/api/v1/material-library",{method:"POST",body:data});
export const createAssignment=(data:AssignmentInput)=>request<Assignment>("/api/v1/assignments",{method:"POST",body:data});
/** PUT con control de versión: el servidor responde 409 si otra persona modificó la actividad. */
export const updateAssignment=(id:string,data:AssignmentInput,expectedVersion:number)=>
  request<Assignment>(`/api/v1/assignments/${encodeURIComponent(id)}`,{method:"PUT",body:data,query:{expected_version:expectedVersion}});
export const getSubmissions=(assignmentId?:string)=>request<Submission[]>("/api/v1/submissions",{query:{assignment_id:assignmentId}});
export type SubmissionOutcome={queued:true;operation_id:string}|(Submission&{queued?:false});
/** Envía la respuesta; sin conexión (o si falla la red) la guarda en la cola local para sincronizarla después. */
export async function createSubmission(assignmentId:string,answer:string,baseVersion=0):Promise<SubmissionOutcome>{
  if(!navigator.onLine)return {queued:true,operation_id:await queueSubmission(assignmentId,answer,baseVersion)};
  try{
    return await request<Submission>("/api/v1/submissions",{method:"POST",body:{assignment_id:assignmentId,answer,client_updated_at:new Date().toISOString()}});
  }catch(error){
    if((error as ApiError).kind==="network")return {queued:true,operation_id:await queueSubmission(assignmentId,answer,baseVersion)};
    throw error;
  }
}
