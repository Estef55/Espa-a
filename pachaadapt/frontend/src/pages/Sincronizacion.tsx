import {useMemo,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {usePendingOps} from "../hooks/usePendingOps";
import {retryRejected,synchronize,queueSubmission} from "../offline/sync-queue";
import {localDB} from "../offline/local-db";
import {fetchAssignments,getSubmissions} from "../services/assignments.service";
import {getServerSyncStatus,pullChanges} from "../services/sync.service";
import {planResolution,type Choice,type SyncConflict} from "../lib/conflicts";
import {dateLabel} from "../lib/format";
import type {SyncPull,SyncServerStatus} from "../lib/types";
import {ErrorNotice,Notice,PageHeader,Panel} from "../components/ui";

const asError=(e:unknown)=>e instanceof Error?e:new Error(String(e));

function ConflictCard({conflict}:{conflict:SyncConflict}){
  const {removeConflict}=useApp();
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");
  async function resolve(choice:Choice){
    setBusy(true);setError(null);setProblem("");
    try{
      let fetched:number|undefined;
      if(choice==="local"&&!conflict.server){
        const list=await getSubmissions(conflict.operation.payload.assignment_id);
        fetched=list[0]?.server_version;
      }
      const plan=planResolution(conflict,choice,fetched);
      if(plan.missingServerVersion){setProblem("No se pudo conocer la versión actual del servidor. Inténtalo de nuevo con conexión.");return;}
      await localDB.remove(plan.removeOperationId);
      if(plan.requeue)await queueSubmission(plan.requeue.assignmentId,plan.requeue.answer,plan.requeue.baseVersion);
      removeConflict(plan.removeOperationId);window.dispatchEvent(new Event("pacha-sync-change"));
      if(plan.requeue)await synchronize();
    }catch(e){setError(asError(e));}finally{setBusy(false);}
  }
  return <li className="card conflict"><h3>Conflicto en una respuesta</h3>
    <p className="hint">La entrega cambió en el servidor mientras el dispositivo estaba sin conexión. Elige qué versión conservar.</p>
    <div className="grid-2"><div><strong>En el servidor{conflict.server?` (versión ${conflict.server.server_version})`:""}</strong><p className="prewrap">{conflict.server?.answer??"No disponible para este tipo de conflicto."}</p></div>
    <div><strong>En este dispositivo</strong><p className="prewrap">{conflict.operation.payload.answer}</p></div></div>
    {problem&&<Notice kind="error">{problem}</Notice>}{error&&<ErrorNotice error={error}/>}
    <div className="row"><button className="btn" disabled={busy} onClick={()=>void resolve("server")}>Conservar la del servidor</button><button className="btn btn-primary" disabled={busy} onClick={()=>void resolve("local")}>Enviar la mía</button></div></li>;
}

export default function Sincronizacion(){
  const {profile,online,sync,conflicts,events}=useApp();
  const ops=usePendingOps();
  const acts=useAsync(fetchAssignments,[profile.user,profile.role]);
  const titles=useMemo(()=>new Map((acts.data?.data??[]).map(a=>[a.id,a.title])),[acts.data]);
  const [status,setStatus]=useState<SyncServerStatus|null>(null);const [pull,setPull]=useState<SyncPull|null>(null);
  const [error,setError]=useState<Error|null>(null);const [busy,setBusy]=useState("");
  const student=profile.role==="student";
  async function run(name:string,job:()=>Promise<void>){setBusy(name);setError(null);try{await job();}catch(e){setError(asError(e));}finally{setBusy("");}}
  const lastPullKey=`pacha-last-pull:${profile.user}`;
  return <>
    <PageHeader title="Conexión y sincronización" description="Las respuestas escritas sin conexión se guardan en este dispositivo y se envían al servidor cuando vuelve la conexión."/>
    <Panel title="Estado">
      <dl className="kv"><div className="kv-row"><dt>Conexión</dt><dd><span className={`dot ${online?"ok":"off"}`}/>{online?"Con conexión":"Sin conexión"}</dd></div>
        <div className="kv-row"><dt>Respuestas pendientes</dt><dd>{sync.pending}</dd></div>
        {!!sync.otherProfiles&&<div className="kv-row"><dt>Pendientes de otros perfiles</dt><dd>{sync.otherProfiles} (se envían al volver a ese perfil)</dd></div>}
        <div className="kv-row"><dt>Última confirmación del servidor</dt><dd>{sync.lastSync?dateLabel(sync.lastSync):"Ninguna todavía"}</dd></div>
        <div className="kv-row"><dt>Estado</dt><dd>{sync.syncing?"Sincronizando…":"En reposo"}</dd></div></dl>
      <p className="hint">Sincronización automática: al abrir la aplicación, al recuperar la conexión y con reintentos espaciados si el servidor falla. Solo se sincronizan respuestas de estudiantes.</p>
      <div className="row"><button className="btn btn-primary" onClick={()=>void synchronize()} disabled={!online||sync.syncing||!student}>{sync.syncing?"Sincronizando…":"Sincronizar ahora"}</button>
        {!student&&<span className="hint">La cola solo existe para el perfil Estudiante.</span>}</div>
    </Panel>
    {conflicts.length>0&&<Panel title="Conflictos por resolver"><ul className="cards">{conflicts.map(c=><ConflictCard key={c.operation.operation_id} conflict={c}/>)}</ul></Panel>}
    {ops.some(o=>o.rejection)&&<Notice kind="warn">El servidor rechazó algunas respuestas. Se conservan en este dispositivo y no se reintentarán automáticamente; revisa el motivo y pulsa «Volver a intentar» cuando corresponda.</Notice>}
    <Panel title="Cola pendiente">
      {!ops.length?<p className="hint">No hay respuestas pendientes para este perfil.</p>:
      <div className="table-wrap"><table className="data"><caption className="sr-only">Respuestas pendientes de envío</caption><thead><tr><th scope="col">Actividad</th><th scope="col">Guardada</th><th scope="col">Intentos</th><th scope="col">Respuesta / estado</th><th scope="col">Acción</th></tr></thead>
        <tbody>{ops.map(o=><tr key={o.operation_id}><th scope="row">{titles.get(o.entity_id)??o.entity_id}</th><td>{dateLabel(o.created_at)}</td><td>{o.attempts}</td><td className="clip">{o.payload.answer}{o.rejection&&<p className="hint">Rechazo HTTP {o.rejection.status}{o.rejection.reason?`: ${o.rejection.reason}`:""}</p>}</td><td>{o.rejection&&<button className="btn btn-quiet" disabled={!online||busy!==""} onClick={()=>void run(`retry:${o.operation_id}`,async()=>{await retryRejected(o.operation_id);})}>{busy===`retry:${o.operation_id}`?"Reintentando…":"Volver a intentar"}</button>}</td></tr>)}</tbody></table></div>}
    </Panel>
    {events.length>0&&<Panel title="Avisos recientes"><ul className="plain">{events.map(e=><li key={e.id}>{dateLabel(e.at)}: {e.text}</li>)}</ul></Panel>}
    <Panel title="Servidor" description="Consulta directa a los endpoints de sincronización.">
      <div className="row"><button className="btn" disabled={!online||!!busy} onClick={()=>void run("status",async()=>setStatus(await getServerSyncStatus()))}>{busy==="status"?"Consultando…":"Consultar estado del servidor"}</button>
        <button className="btn" disabled={!online||!!busy} onClick={()=>void run("pull",async()=>{const since=localStorage.getItem(lastPullKey)??undefined;const r=await pullChanges(since);localStorage.setItem(lastPullKey,r.server_time);setPull(r);acts.reload();})}>{busy==="pull"?"Buscando…":"Buscar cambios en el servidor"}</button></div>
      {error&&<ErrorNotice error={error}/>}
      {status&&<dl className="kv"><div className="kv-row"><dt>Servidor</dt><dd>{status.server}</dd></div><div className="kv-row"><dt>Operaciones aceptadas (24 h)</dt><dd>{status.accepted_last_24h}</dd></div><div className="kv-row"><dt>Última recibida</dt><dd>{dateLabel(status.last_received_at,"ninguna")}</dd></div><div className="kv-row"><dt>Usuario reconocido</dt><dd>{status.actor_id}</dd></div></dl>}
      {pull&&<Notice kind="success">Desde la última búsqueda hay {pull.assignments.length} actividad(es) y {pull.submissions.length} entrega(s) con cambios. Las listas se actualizaron.</Notice>}
    </Panel>
  </>;
}
