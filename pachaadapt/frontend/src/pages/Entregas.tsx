import {useMemo,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {usePendingOps} from "../hooks/usePendingOps";
import {fetchAssignments,getSubmissions,reviewSubmission} from "../services/assignments.service";
import {can} from "../lib/permissions";
import {buildSubmissionsCsv,downloadText} from "../lib/csv";
import {dateLabel} from "../lib/format";
import type {Submission} from "../lib/types";
import {EmptyState,ErrorNotice,Field,Loading,Notice,PageHeader,StatusPill} from "../components/ui";

export default function Entregas(){
  const {profile,online}=useApp();
  const staff=can(profile.role,"submissions.review"),student=profile.role==="student";
  const dep=[profile.user,profile.role];
  const subs=useAsync(()=>getSubmissions(),dep);
  const acts=useAsync(fetchAssignments,dep);
  const pendingOps=usePendingOps();
  const [activity,setActivity]=useState("all"),[status,setStatus]=useState("all"),[search,setSearch]=useState("");
  const [busyId,setBusyId]=useState<string|null>(null);const [rowError,setRowError]=useState<{id:string;error:Error}|null>(null);const [message,setMessage]=useState("");
  const [gradeDrafts,setGradeDrafts]=useState<Record<string,{score:string;maxScore:string}>>({});
  const [gradeErrors,setGradeErrors]=useState<Record<string,string>>({});
  const titles=useMemo(()=>new Map((acts.data?.data??[]).map(a=>[a.id,a.title])),[acts.data]);
  const titleOf=(id:string)=>titles.get(id);
  const all=subs.data??[];
  const shown=all.filter(s=>(activity==="all"||s.assignment_id===activity)&&(status==="all"||s.status===status)&&(!search.trim()||s.student_id.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())||s.answer.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())));

  async function review(item:Submission,next:"reviewed"|"returned",validate=false){
    setBusyId(item.id);setRowError(null);setMessage("");
    try{
      let details:{score?:number;max_score?:number;validation_status?:"pending"|"validated"|"rejected"}={};
      if(validate){
        const draft=gradeDrafts[item.id]??{score:item.score==null?"":String(item.score),maxScore:item.max_score==null?"":String(item.max_score)};
        const score=Number(draft.score),maxScore=Number(draft.maxScore);
        if(!draft.score.trim()||!draft.maxScore.trim()||!Number.isFinite(score)||!Number.isFinite(maxScore)||maxScore<=0||score<0||score>maxScore){
          setGradeErrors(errors=>({...errors,[item.id]:"Ingresa una puntuación válida: 0 ≤ puntuación ≤ máximo, y máximo mayor que 0."}));
          return;
        }
        if(!window.confirm("La calificación validada se incorporará a los informes y no se podrá modificar. ¿Deseas continuar?"))return;
        details={score,max_score:maxScore,validation_status:"validated"};
      }else if(next==="reviewed"){
        const draft=gradeDrafts[item.id]??{score:item.score==null?"":String(item.score),maxScore:item.max_score==null?"":String(item.max_score)};
        if(draft.score.trim()||draft.maxScore.trim()){
          const score=Number(draft.score),maxScore=Number(draft.maxScore);
          if(!draft.score.trim()||!draft.maxScore.trim()||!Number.isFinite(score)||!Number.isFinite(maxScore)||maxScore<=0||score<0||score>maxScore){
            setGradeErrors(errors=>({...errors,[item.id]:"Completa ambas puntuaciones o deja ambas vacías; la puntuación debe estar entre 0 y el máximo."}));
            return;
          }
          details={score,max_score:maxScore,validation_status:"pending"};
        }
      }
      setGradeErrors(errors=>{const next={...errors};delete next[item.id];return next;});
      await reviewSubmission(item.id,{status:next,...details});
      setMessage(validate?"Calificación validada; ya puede incluirse en los informes.":next==="reviewed"?"Entrega revisada. Si ingresaste una nota, queda pendiente de validación.":"Entrega devuelta al estudiante.");
      subs.reload();
    }catch(err){setRowError({id:item.id,error:err instanceof Error?err:new Error(String(err))});}finally{setBusyId(null);}
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
      {(staff||s.validation_status==="validated")&&s.score!=null&&s.max_score!=null&&<p className="meta"><span>Calificación: <strong>{s.score} / {s.max_score}</strong></span><span>Resultado: {s.validation_status==="validated"?"Validado para informes":"Pendiente de validación"}</span></p>}
      {student&&s.validation_status!=="validated"&&s.status==="reviewed"&&<Notice kind="info">La entrega fue revisada; todavía no hay una calificación validada para mostrar en informes.</Notice>}
      {staff&&s.validation_status==="validated"&&<Notice kind="success">Calificación validada y protegida; ya puede alimentar informes pedagógicos.</Notice>}
      {staff&&s.validation_status!=="validated"&&<div className="answer">
        <h3>Revisión docente</h3>
        <div className="grid-2">
          <Field label="Puntuación (opcional al revisar)" hint="Ingresa también el máximo para guardar una nota pendiente de validación."><input type="number" min={0} step="any" value={gradeDrafts[s.id]?.score??(s.score==null?"":String(s.score))} onChange={e=>setGradeDrafts(d=>({...d,[s.id]:{score:e.target.value,maxScore:d[s.id]?.maxScore??(s.max_score==null?"":String(s.max_score))}}))} disabled={busyId===s.id}/></Field>
          <Field label="Puntaje máximo"><input type="number" min={0.01} step="any" value={gradeDrafts[s.id]?.maxScore??(s.max_score==null?"":String(s.max_score))} onChange={e=>setGradeDrafts(d=>({...d,[s.id]:{score:d[s.id]?.score??(s.score==null?"":String(s.score)),maxScore:e.target.value}}))} disabled={busyId===s.id}/></Field>
        </div>
        {gradeErrors[s.id]&&<Notice kind="error">{gradeErrors[s.id]}</Notice>}
        <div className="row">
          <button className="btn" disabled={busyId===s.id||!online} onClick={()=>void review(s,"reviewed")}>{busyId===s.id?"Guardando…":"Guardar revisión"}</button>
          <button className="btn btn-primary" disabled={busyId===s.id||!online} onClick={()=>void review(s,"reviewed",true)}>{busyId===s.id?"Guardando…":"Validar calificación"}</button>
          <button className="btn btn-quiet" disabled={busyId===s.id||!online||s.status==="returned"} onClick={()=>void review(s,"returned")}>Devolver</button>
        </div>
      </div>}
      {rowError?.id===s.id&&<ErrorNotice error={rowError.error}/>}
    </li>)}</ul>}
    {staff&&<p className="hint">Al validar una calificación se envía al servidor junto con el estado revisado; los resultados validados no pueden modificarse y son los únicos que alimentan los informes.</p>}
  </>;
}
