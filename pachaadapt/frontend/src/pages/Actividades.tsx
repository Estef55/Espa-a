import {useEffect,useMemo,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {usePendingOps} from "../hooks/usePendingOps";
import {clearDraft,getDraft,saveDraft} from "../offline/adaptation-store";
import {createAssignment,createSubmission,fetchAssignments,getSubmissions,updateAssignment} from "../services/assignments.service";
import {can} from "../lib/permissions";
import {isSubmissionLocked} from "../lib/submissions";
import {dateLabel,fromLocalInput,toLocalInput} from "../lib/format";
import type {Assignment,Submission} from "../lib/types";
import {CachedNotice,EmptyState,ErrorNotice,Field,Loading,Notice,OfflineNotice,PageHeader,StatusPill} from "../components/ui";

type Draft={title:string;instructions:string;due:string;status:"draft"|"published"|"closed"};
const EMPTY:Draft={title:"",instructions:"",due:"",status:"published"};

function AssignmentForm({initial,editing,onSaved,onCancel,onConflict}:{initial:Draft;editing?:Assignment;onSaved:(message:string)=>void;onCancel:()=>void;onConflict:()=>void}){
  const {online}=useApp();
  const [draft,setDraft]=useState(initial);const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");
  const set=<K extends keyof Draft>(key:K,value:Draft[K])=>setDraft(d=>({...d,[key]:value}));
  async function submit(e:React.FormEvent){
    e.preventDefault();setError(null);
    if(!draft.title.trim())return setProblem("Escribe el título de la actividad.");
    if(draft.title.length>200)return setProblem("El título admite hasta 200 caracteres.");
    if(draft.instructions.length>10000)return setProblem("Las instrucciones admiten hasta 10 000 caracteres.");
    setProblem("");setBusy(true);
    try{
      const data={title:draft.title.trim(),instructions:draft.instructions,status:draft.status,due_at:fromLocalInput(draft.due)};
      if(editing)await updateAssignment(editing.id,data,editing.version);else await createAssignment(data);
      onSaved(editing?"Actividad actualizada.":draft.status==="published"?"Actividad publicada.":"Actividad guardada como borrador.");
    }catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  return <form className="panel form" onSubmit={e=>void submit(e)} noValidate aria-label={editing?"Editar actividad":"Nueva actividad"}>
    <h2>{editing?`Editar actividad (versión ${editing.version})`:"Nueva actividad"}</h2>
    <div className="grid-2">
      <Field label="Título"><input value={draft.title} onChange={e=>set("title",e.target.value)} maxLength={200} required aria-invalid={!!problem&&!draft.title.trim()}/></Field>
      <Field label="Fecha límite (opcional)"><input type="datetime-local" value={draft.due} onChange={e=>set("due",e.target.value)}/></Field>
    </div>
    <Field label="Instrucciones" hint={`${draft.instructions.length} / 10 000 caracteres`}><textarea rows={5} value={draft.instructions} onChange={e=>set("instructions",e.target.value)}/></Field>
    <Field label="Estado" hint="Los estudiantes solo ven las actividades publicadas."><select value={draft.status} onChange={e=>set("status",e.target.value as Draft["status"])}>
      <option value="published">Publicada</option><option value="draft">Borrador</option>{editing&&<option value="closed">Cerrada</option>}</select></Field>
    {problem&&<Notice kind="error">{problem}</Notice>}
    {error&&<ErrorNotice error={error} onRetry={(error as {kind?:string}).kind==="conflict"?onConflict:undefined} retryLabel="Recargar actividades"/>}
    <OfflineNotice what="Guardar actividades"/>
    <div className="row"><button className="btn btn-primary" disabled={busy||!online}>{busy?"Guardando…":editing?"Guardar cambios":draft.status==="published"?"Publicar actividad":"Guardar borrador"}</button><button type="button" className="btn btn-quiet" onClick={onCancel}>Cancelar</button></div>
  </form>;
}

function AnswerBox({assignment,previous,pending,user,onSent}:{assignment:Assignment;previous?:Submission;pending:boolean;user:string;onSent:(message:string)=>void}){
  const [text,setText]=useState("");const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);
  useEffect(()=>{let active=true;void getDraft(user,assignment.id).then(draft=>{if(active&&draft)setText(draft.answer);}).catch(()=>undefined);return()=>{active=false;};},[user,assignment.id]);
  async function send(){
    setBusy(true);setError(null);
    try{
      const result=await createSubmission(assignment.id,text.trim(),previous?.server_version??0);
      await clearDraft(user,assignment.id).catch(()=>undefined);
      setText("");onSent(result.queued?"Respuesta guardada en este dispositivo; se enviará al recuperar la conexión.":"Respuesta recibida por el servidor.");
    }catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  const locked=isSubmissionLocked(previous);
  return <div className="answer">
    {previous&&<p className="hint">Última respuesta enviada ({dateLabel(previous.updated_at)}): <StatusPill status={previous.status}/> versión {previous.server_version}</p>}
    {locked&&<Notice kind="warn">El servidor bloquea las entregas revisadas o devueltas y esta versión no tiene una acción para reabrirlas. Contacta al docente; no se intentará un reenvío que el backend rechazará.</Notice>}
    {pending&&<Notice kind="info">Tienes una respuesta pendiente de envío para esta actividad. Revisa <a href="#/sincronizacion">Conexión y sincronización</a>.</Notice>}
    <Field label={previous?"Actualizar tu respuesta":"Tu respuesta"} hint={`${text.length} / 50 000 caracteres`}>
      <textarea rows={4} maxLength={50000} value={text} disabled={locked} onChange={e=>{const value=e.target.value;setText(value);void saveDraft(user,assignment.id,value).catch(()=>undefined);}} aria-label={`Respuesta para ${assignment.title}`}/></Field>
    {error&&<ErrorNotice error={error}/>}
    <button className="btn btn-primary" disabled={busy||!text.trim()||locked} onClick={()=>void send()}>{busy?"Enviando…":previous?"Actualizar respuesta":"Enviar respuesta"}</button>
  </div>;
}

export default function Actividades(){
  const {profile,online}=useApp();
  const staff=can(profile.role,"assignments.write"),student=profile.role==="student";
  const dep=[profile.user,profile.role];
  const list=useAsync(fetchAssignments,dep);
  const subs=useAsync(()=>student?getSubmissions():Promise.resolve([] as Submission[]),dep);
  const pendingOps=usePendingOps();
  const [search,setSearch]=useState(""),[filter,setFilter]=useState("all");
  const [mode,setMode]=useState<{kind:"none"}|{kind:"new"}|{kind:"edit";item:Assignment}>({kind:"none"});
  const [message,setMessage]=useState("");
  const items=list.data?.data??[];
  const shown=useMemo(()=>{const q=search.trim().toLocaleLowerCase();return items.filter(a=>(!q||a.title.toLocaleLowerCase().includes(q)||a.instructions.toLocaleLowerCase().includes(q))&&(filter==="all"||a.status===filter));},[items,search,filter]);
  const bySubmission=new Map((subs.data??[]).map(s=>[s.assignment_id,s]));
  const pendingIds=new Set(pendingOps.map(o=>o.entity_id));
  const canEdit=(a:Assignment)=>profile.role==="admin"||a.created_by===profile.user;
  const saved=(text:string)=>{setMessage(text);setMode({kind:"none"});list.reload();};

  return <>
    <PageHeader title="Actividades" description={staff?"Crea, edita, busca y filtra las actividades.":"Lee las actividades publicadas y envía tus respuestas."}
      actions={<>{staff&&mode.kind==="none"&&<button className="btn btn-primary" onClick={()=>{setMessage("");setMode({kind:"new"});}} disabled={!online}>Nueva actividad</button>}<button className="btn" onClick={()=>{list.reload();subs.reload();}} disabled={list.loading}>{list.loading?"Actualizando…":"Actualizar"}</button></>}/>
    {message&&<Notice kind="success">{message}</Notice>}
    {mode.kind==="new"&&<AssignmentForm initial={EMPTY} onSaved={saved} onCancel={()=>setMode({kind:"none"})} onConflict={list.reload}/>}
    {mode.kind==="edit"&&<AssignmentForm key={mode.item.id} initial={{title:mode.item.title,instructions:mode.item.instructions,due:toLocalInput(mode.item.due_at),status:mode.item.status as Draft["status"]}} editing={mode.item} onSaved={saved} onCancel={()=>setMode({kind:"none"})} onConflict={()=>{setMode({kind:"none"});list.reload();}}/>}
    {list.data?.fromCache&&<CachedNotice savedAt={list.data.savedAt}/>}
    {list.error&&<ErrorNotice error={list.error} onRetry={list.reload}/>}
    {student&&subs.error&&online&&<Notice kind="warn">No se pudo comprobar tus entregas anteriores: {subs.error.message}</Notice>}
    <div className="toolbar">
      <input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar por título o instrucciones" aria-label="Buscar actividades"/>
      {staff&&<select value={filter} onChange={e=>setFilter(e.target.value)} aria-label="Filtrar por estado"><option value="all">Todos los estados</option><option value="published">Publicadas</option><option value="draft">Borradores</option><option value="closed">Cerradas</option></select>}
    </div>
    {list.loading&&!list.data?<Loading label="Cargando actividades…"/>:!list.error&&!shown.length?
      <EmptyState title={items.length?"Ninguna actividad coincide con la búsqueda":"Todavía no hay actividades"}>{items.length?"Prueba con otro texto o cambia el filtro.":staff?"Crea la primera con «Nueva actividad».":"Cuando tu docente publique una, aparecerá aquí."}</EmptyState>:
    <ul className="cards">{shown.map(a=>{
      const overdue=!!a.due_at&&new Date(a.due_at).getTime()<Date.now()&&a.status==="published";
      return <li className="card" key={a.id}>
        <div className="card-head"><h2>{a.title}</h2><StatusPill status={a.status}/></div>
        <p className="prewrap">{a.instructions||"Sin instrucciones adicionales."}</p>
        <p className="meta"><span>Fecha límite: {dateLabel(a.due_at,"sin fecha límite")}{overdue&&" (vencida)"}</span><span>Versión {a.version}</span>{staff&&a.created_by&&<span>Creada por {a.created_by}</span>}</p>
        {staff&&<div className="row"><button className="btn" disabled={!online||!canEdit(a)} onClick={()=>{setMessage("");setMode({kind:"edit",item:a});}} title={canEdit(a)?undefined:"Solo quien creó la actividad (o un administrador) puede editarla."}>Editar</button>{!canEdit(a)&&<span className="hint">Solo la persona que la creó puede editarla.</span>}</div>}
        {student&&a.status==="published"&&<AnswerBox key={`${profile.user}:${a.id}`} assignment={a} previous={bySubmission.get(a.id)} pending={pendingIds.has(a.id)} user={profile.user} onSent={text=>{setMessage(text);subs.reload();}}/>}
      </li>;})}</ul>}
  </>;
}
