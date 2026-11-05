import {localDB, type PendingOperation} from "./local-db.ts";
const API = import.meta.env?.VITE_API_URL ?? "";
let running=false;
let retryTimer:ReturnType<typeof setTimeout>|undefined;
const MAX_RETRY_DELAY_MS = 5 * 60 * 1000;
const BASE_RETRY_DELAY_MS = 1500;

function scheduleRetry(attempts:number) {
  if (retryTimer) clearTimeout(retryTimer);
  // Backoff exponencial con jitter para evitar que varios dispositivos reintenten a la vez.
  const exponential = Math.min(MAX_RETRY_DELAY_MS, BASE_RETRY_DELAY_MS * (2 ** Math.min(attempts, 8)));
  const jitter = Math.floor(exponential * (0.15 * Math.random()));
  retryTimer = setTimeout(() => {
    retryTimer = undefined;
    void synchronize();
  }, exponential + jitter);
}
function currentActor(){return {id:localStorage.getItem("pacha-user")??"demo-student",role:localStorage.getItem("pacha-role")??"student"};}
function headers(){const a=currentActor();return {"Content-Type":"application/json","X-User-Id":a.id,"X-Role":a.role};}
/** Una operación pertenece al perfil activo si coincide su actor; las antiguas (sin actor) se tratan como del perfil activo. */
export function belongsToCurrentActor(op:PendingOperation){const a=currentActor();return !op.actor||(op.actor.id===a.id&&op.actor.role===a.role);}
export async function queueSubmission(assignmentId:string,answer:string,baseVersion=0) {
  const op:PendingOperation={operation_id:crypto.randomUUID(),entity_type:"submission",
    entity_id:assignmentId,payload:{assignment_id:assignmentId,answer,base_version:baseVersion,client_updated_at:new Date().toISOString()},
    created_at:new Date().toISOString(),attempts:0,actor:currentActor()};
  await localDB.enqueue(op); window.dispatchEvent(new Event("pacha-sync-change"));
  if(navigator.onLine) void synchronize();
  return op.operation_id;
}
export async function retryRejected(operationId:string) {
  const op=(await localDB.all()).find(item=>item.operation_id===operationId&&belongsToCurrentActor(item));
  if(!op?.rejection)return;
  await localDB.remove(operationId);
  await queueSubmission(op.entity_id,op.payload.answer,op.payload.base_version);
  window.dispatchEvent(new Event("pacha-sync-change"));
  if(navigator.onLine)void synchronize();
}
export async function synchronize() {
  if(running || !navigator.onLine) return;
  running=true;window.dispatchEvent(new Event("pacha-sync-start"));
  let retryAttempts = 0;
  try {
    for(const op of (await localDB.all()).filter(op=>belongsToCurrentActor(op)&&!op.rejection)) {
      try {
        const response=await fetch(`${API}/api/v1/synchronization/push`,{
          method:"POST",headers:headers(),body:JSON.stringify([op]),signal:AbortSignal.timeout(12000)
        });
        if(!response.ok) {
          if(response.status===409) { window.dispatchEvent(new CustomEvent("pacha-sync-conflict",{detail:{operation:op}})); continue; }
          if(response.status>=400 && response.status<500 && ![408,425,429].includes(response.status)) {
            await localDB.enqueue({...op,rejection:{status:response.status,rejected_at:new Date().toISOString()}});
            window.dispatchEvent(new CustomEvent("pacha-sync-rejected",{detail:{operation:op,status:response.status}}));
            continue;
          }
          throw new Error(`HTTP ${response.status}`);
        }
        const body=await response.json(), result=body.results?.[0];
        if(!result || !["acknowledged","rejected","conflict"].includes(result.status)) {
          throw new Error("Respuesta de sincronización no reconocida");
        }
        if(result.status==="acknowledged") {
          await localDB.remove(op.operation_id);
          localStorage.setItem("pacha-last-sync",new Date().toISOString());
        } else if(result.status==="rejected") {
          const reason=typeof result.reason==="string"?result.reason:"server_rejected";
          await localDB.enqueue({...op,rejection:{status:200,reason,rejected_at:new Date().toISOString()}});
          window.dispatchEvent(new CustomEvent("pacha-sync-rejected",{detail:{operation:op,status:200,reason}}));
        } else if(result.status==="conflict") {
          window.dispatchEvent(new CustomEvent("pacha-sync-conflict",{detail:{...result,operation:op}}));
        }
      } catch {
        retryAttempts = op.attempts + 1;
        await localDB.enqueue({...op,attempts:retryAttempts});
        break;
      }
    }
  } finally {
    running=false;
    window.dispatchEvent(new Event("pacha-sync-change"));
    window.dispatchEvent(new Event("pacha-sync-end"));
    if (retryAttempts > 0 && navigator.onLine) scheduleRetry(retryAttempts);
  }
}
window.addEventListener("online",()=>{
  if (retryTimer) clearTimeout(retryTimer);
  retryTimer=undefined;
  void synchronize();
});
