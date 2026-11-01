// Resolución de conflictos de sincronización (lógica pura y probada; los efectos los aplica la interfaz).
import type {Submission} from "./types";
export type QueuedOp={operation_id:string;entity_id:string;payload:{assignment_id:string;answer:string;base_version:number;client_updated_at:string}};
export type SyncConflict={operation:QueuedOp;server?:Submission};
export type Choice="server"|"local";
export type Plan={removeOperationId:string;requeue?:{assignmentId:string;answer:string;baseVersion:number};missingServerVersion?:boolean};

/** Interpreta el detalle del evento "pacha-sync-conflict" emitido por sync-queue. */
export function conflictFromEvent(detail:unknown):SyncConflict|null{
  const d=detail as {operation?:QueuedOp;server?:Submission}|null|undefined;
  if(!d?.operation?.operation_id||!d.operation.payload)return null;
  return {operation:d.operation,server:d.server};
}
/** Conservar servidor: se descarta la operación local. Enviar la mía: se vuelve a encolar sobre la versión vigente. */
export function planResolution(conflict:SyncConflict,choice:Choice,fetchedServerVersion?:number):Plan{
  const removeOperationId=conflict.operation.operation_id;
  if(choice==="server")return {removeOperationId};
  const baseVersion=conflict.server?.server_version??fetchedServerVersion;
  if(baseVersion===undefined)return {removeOperationId,missingServerVersion:true};
  return {removeOperationId,requeue:{assignmentId:conflict.operation.payload.assignment_id,answer:conflict.operation.payload.answer,baseVersion}};
}
