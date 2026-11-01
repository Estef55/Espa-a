import {useMemo,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {usePendingOps} from "../hooks/usePendingOps";
import {fetchAssignments,getSubmissions,reviewSubmission} from "../services/assignments.service";
import {can} from "../lib/permissions";
import {buildSubmissionsCsv,downloadText} from "../lib/csv";
import {dateLabel} from "../lib/format";
import type {Submission} from "../lib/types";
import {EmptyState,ErrorNotice,Loading,Notice,PageHeader,StatusPill} from "../components/ui";

export default function Entregas(){
  const {profile,online}=useApp();
  const staff=can(profile.role,"submissions.review"),student=profile.role==="student";
  const dep=[profile.user,profile.role];
  const subs=useAsync(()=>getSubmissions(),dep);
  const acts=useAsync(fetchAssignments,dep);
  const pendingOps=usePendingOps();
  const [activity,setActivity]=useState("all"),[status,setStatus]=useState("all"),[search,setSearch]=useState("");
  const [busyId,setBusyId]=useState<string|null>(null);const [rowError,setRowError]=useState<{id:string;error:Error}|null>(null);const [message,setMessage]=useState("");
  const titles=useMemo(()=>new Map((acts.data?.data??[]).map(a=>[a.id,a.title])),[acts.data]);
  const titleOf=(id:string)=>titles.get(id);
  const all=subs.data??[];
  const shown=all.filter(s=>(activity==="all"||s.assignment_id===activity)&&(status==="all"||s.status===status)&&(!search.trim()||s.student_id.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())||s.answer.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())));

  async function review(item:Submission,next:"reviewed"|"returned"){
    setBusyId(item.id);setRowError(null);setMessage("");
    try{await reviewSubmission(item.id,next);setMessage(next==="reviewed"?"Entrega marcada como revisada.":"Entrega devuelta al estudiante.");subs.reload();}
    catch(err){setRowError({id:item.id,error:err instanceof Error?err:new Error(String(err))});}finally{setBusyId(null);}
  }
  const exportCsv=()=>downloadText("entregas_pachaadapt.csv",buildSubmissionsCsv(shown,titleOf));

  return <>
    <PageHeader title={student?"Mis entregas":"Entregas recibidas"} description={student?"Estado de las respuestas que enviaste.":"Revisa, devuelve y exporta las respuestas de tus actividades."}
      actions={<><button className="btn" onClick={()=>subs.reload()} disabled={subs.loading}>{subs.loading?"Actualizando…":"Actualizar"}</button>{staff&&<button className="btn" onClick={exportCsv} disabled={!shown.length} title="Genera el archivo en este navegador con las entregas visibles">Exportar CSV</button>}</>}/>
    {message&&<Notice kind="success">{message}</Notice>}
    {student&&pendingOps.length>0&&<Notice kind="info" action={<a className="btn btn-quiet" href="#/sincronizacion">Ver cola</a>}><strong>{pendingOps.length} respuesta(s) pendiente(s) de envío.</strong> Se enviarán al recuperar la conexión.</Notice>}
    {subs.error&&<ErrorNotice error={subs.error} onRetry={subs.reload}/>}
    {!student&&<p className="hint">Con perfil docente solo se muestran las entregas de actividades creadas por ti. La exportación CSV se genera en el navegador (el servidor no tiene endpoint de exportación).</p>}
    {staff&&<div className="toolbar">
      <input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar por estudiante o respuesta" aria-label="Buscar entregas"/>
      <select value={activity} onChange={e=>setActivity(e.target.value)} aria-label="Filtrar por actividad"><option value="all">Todas las actividades</option>{(acts.data?.data??[]).map(a=><option key={a.id} value={a.id}>{a.title}</option>)}</select>
      <select value={status} onChange={e=>setStatus(e.target.value)} aria-label="Filtrar por estado"><option value="all">Todos los estados</option><option value="submitted">Entregadas</option><option value="reviewed">Revisadas</option><option value="returned">Devueltas</option></select>
    </div>}
    {subs.loading&&!subs.data?<Loading label="Cargando entregas…"/>:!subs.error&&!shown.length?
      <EmptyState title={all.length?"Ninguna entrega coincide con los filtros":"Todavía no hay entregas"}>{all.length?"Cambia los filtros para ver más.":student?"Responde una actividad desde la sección Actividades.":"Aparecerán aquí cuando tus estudiantes envíen respuestas."}</EmptyState>:
    <ul className="cards">{shown.map(s=><li className="card" key={s.id}>
      <div className="card-head"><h2>{titleOf(s.assignment_id)??"Actividad"}</h2><StatusPill status={s.status}/></div>
      {staff&&<p className="meta"><span>Estudiante: <strong>{s.student_id}</strong></span></p>}
      <p className="prewrap">{s.answer}</p>
      <p className="meta"><span>Actualizada: {dateLabel(s.updated_at)}</span><span>Versión {s.server_version}</span></p>
      {staff&&<div className="row">
        <button className="btn btn-primary" disabled={busyId===s.id||s.status==="reviewed"||!online} onClick={()=>void review(s,"reviewed")}>{busyId===s.id?"Guardando…":"Marcar revisada"}</button>
        <button className="btn" disabled={busyId===s.id||s.status==="returned"||!online} onClick={()=>void review(s,"returned")}>Devolver</button>
      </div>}
      {rowError?.id===s.id&&<ErrorNotice error={rowError.error}/>}
    </li>)}</ul>}
    {staff&&<p className="hint">Los estados disponibles en el servidor son entregada, revisada y devuelta. No existen notas ni comentarios por entrega.</p>}
  </>;
}
