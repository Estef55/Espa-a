import {useEffect,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {archiveDocument,createDocument,getDocument,getVersion,importDocument,listDocuments,listVersions,restoreVersion,saveDocument} from "../services/documents.service";
import {dateLabel} from "../lib/format";
import type {DocumentVersionFull} from "../lib/types";
import {EmptyState,ErrorNotice,Field,Gate,Loading,Notice,NotConnected,OfflineNotice,PageHeader,Panel} from "../components/ui";

const asError=(e:unknown)=>e instanceof Error?e:new Error(String(e));

function Editor({id,onChanged}:{id:string;onChanged:()=>void}){
  const {online}=useApp();
  const doc=useAsync(()=>getDocument(id),[id]);
  const versions=useAsync(()=>listVersions(id),[id]);
  const [content,setContent]=useState("");const [base,setBase]=useState(1);const [reason,setReason]=useState("");
  const [viewing,setViewing]=useState<DocumentVersionFull|null>(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [message,setMessage]=useState("");
  useEffect(()=>{if(doc.data){setContent(doc.data.content);setBase(doc.data.current_version);}},[doc.data]);
  const current=doc.data;const dirty=!!current&&content!==current.content;const archived=!!current?.archived;

  async function act(job:()=>Promise<void>){setBusy(true);setError(null);setMessage("");try{await job();}catch(e){setError(asError(e));}finally{setBusy(false);}}
  const save=()=>act(async()=>{const saved=await saveDocument(id,content,base,reason.trim()||undefined);doc.setData(saved);setReason("");setMessage(`Guardado como versión ${saved.current_version}.`);versions.reload();onChanged();});
  const openVersion=(v:number)=>act(async()=>setViewing(await getVersion(id,v)));
  const restore=()=>act(async()=>{
    if(!viewing)return;
    if(dirty&&!window.confirm("Tienes cambios sin guardar que se perderán al restaurar. ¿Continuar?"))return;
    const restored=await restoreVersion(id,viewing.version,base,`Restaurada desde la versión ${viewing.version}`);
    doc.setData(restored);setViewing(null);setMessage(`Versión ${viewing.version} restaurada como versión ${restored.current_version}.`);versions.reload();onChanged();
  });
  const archive=()=>act(async()=>{
    if(!window.confirm("¿Archivar este documento? No se borra, pero ya no se podrá editar."))return;
    await archiveDocument(id);setMessage("Documento archivado.");doc.reload();onChanged();
  });
  const reload=()=>{setError(null);doc.reload();versions.reload();};

  if(doc.loading&&!doc.data)return <Loading label="Cargando documento…"/>;
  if(doc.error)return <ErrorNotice error={doc.error} onRetry={doc.reload}/>;
  if(!current)return null;
  return <div className="stack">
    <Panel title={current.title} description={`Versión ${current.current_version} · actualizado ${dateLabel(current.updated_at)}${current.source_material_id?` · origen: material ${current.source_material_id}`:""}`}
      actions={!archived&&<button className="btn btn-quiet" onClick={()=>void archive()} disabled={busy||!online}>Archivar</button>}>
      {archived&&<Notice kind="info">Documento archivado: se conserva su historial, pero no admite cambios.</Notice>}
      <Field label="Contenido" hint={`${content.length.toLocaleString("es-PE")} caracteres${dirty?" · cambios sin guardar":""}`}><textarea rows={14} value={content} onChange={e=>setContent(e.target.value)} readOnly={archived}/></Field>
      {!archived&&<><Field label="Motivo del cambio (opcional)" hint="Queda registrado en el historial."><input value={reason} onChange={e=>setReason(e.target.value)} maxLength={500}/></Field>
      <div className="row"><button className="btn btn-primary" onClick={()=>void save()} disabled={busy||!dirty||!online}>{busy?"Guardando…":"Guardar nueva versión"}</button><button className="btn btn-quiet" onClick={()=>setContent(current.content)} disabled={!dirty}>Descartar cambios</button></div></>}
      <OfflineNotice what="Guardar documentos"/>
      {message&&<Notice kind="success">{message}</Notice>}
      {error&&<ErrorNotice error={error} onRetry={(error as {kind?:string}).kind==="conflict"?reload:undefined} retryLabel="Recargar documento (descarta lo no guardado)"/>}
    </Panel>
    <Panel title="Historial de versiones" description="Cada guardado crea una versión nueva; restaurar tampoco borra nada.">
      {versions.loading&&!versions.data?<Loading/>:versions.error?<ErrorNotice error={versions.error} onRetry={versions.reload}/>:
      <div className="table-wrap"><table className="data"><caption className="sr-only">Versiones del documento</caption>
        <thead><tr><th scope="col">Versión</th><th scope="col">Fecha</th><th scope="col">Autor</th><th scope="col">Motivo</th><th scope="col">Tamaño</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
        <tbody>{(versions.data??[]).map(v=><tr key={v.version}><th scope="row">{v.version}{v.version===current.current_version&&<span className="hint"> (actual)</span>}</th><td>{dateLabel(v.created_at)}</td><td>{v.author_id}</td><td>{v.reason||"—"}{v.restored_from?` (desde v${v.restored_from})`:""}</td><td>{v.size.toLocaleString("es-PE")}</td><td><button className="btn btn-quiet" onClick={()=>void openVersion(v.version)} disabled={busy||!online}>Ver</button></td></tr>)}</tbody></table></div>}
      {viewing&&<div className="result"><h3>Versión {viewing.version}</h3><pre className="output">{viewing.content}</pre>
        <div className="row">{!archived&&viewing.version!==current.current_version&&<button className="btn btn-primary" onClick={()=>void restore()} disabled={busy||!online}>Restaurar esta versión</button>}<button className="btn btn-quiet" onClick={()=>setViewing(null)}>Cerrar</button></div></div>}
    </Panel>
  </div>;
}

function Inner(){
  const {ai,online}=useApp();
  const [showArchived,setShowArchived]=useState(false);
  const docs=useAsync(()=>listDocuments(showArchived),[showArchived]);
  const [selected,setSelected]=useState<string|null>(null);
  const [form,setForm]=useState({title:"",content:""});const [materialId,setMaterialId]=useState("");
  const [busy,setBusy]=useState("");const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");
  async function create(e:React.FormEvent){
    e.preventDefault();setError(null);
    if(!form.title.trim()||!form.content.trim())return setProblem("Escribe el título y el contenido.");
    setProblem("");setBusy("create");
    try{const d=await createDocument({title:form.title.trim(),content:form.content});setForm({title:"",content:""});setSelected(d.id);docs.reload();}
    catch(err){setError(asError(err));}finally{setBusy("");}
  }
  async function importFrom(e:React.FormEvent){
    e.preventDefault();setError(null);setBusy("import");
    try{const d=await importDocument(materialId.trim());setMaterialId("");setSelected(d.id);docs.reload();}
    catch(err){setError(asError(err));}finally{setBusy("");}
  }
  return <>
    <OfflineNotice what="Editar documentos"/>
    <div className="split">
      <div className="stack">
        <Panel title="Mis documentos" actions={<label className="check"><input type="checkbox" checked={showArchived} onChange={e=>setShowArchived(e.target.checked)}/> Ver archivados</label>}>
          {docs.loading&&!docs.data?<Loading/>:docs.error?<ErrorNotice error={docs.error} onRetry={docs.reload}/>:!docs.data?.length?<EmptyState title="Todavía no hay documentos">Crea uno nuevo o guarda una adaptación desde «Archivos y adaptación».</EmptyState>:
          <ul className="picklist">{docs.data.map(d=><li key={d.id}><button className={`pick ${d.id===selected?"active":""}`} aria-pressed={d.id===selected} onClick={()=>setSelected(d.id)}><strong>{d.title}</strong><span className="hint">v{d.current_version} · {dateLabel(d.updated_at)}{d.archived?" · archivado":""}</span></button></li>)}</ul>}
        </Panel>
        <Panel title="Nuevo documento">
          <form className="form" onSubmit={e=>void create(e)} noValidate>
            <Field label="Título"><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} maxLength={200}/></Field>
            <Field label="Contenido"><textarea rows={5} value={form.content} onChange={e=>setForm({...form,content:e.target.value})}/></Field>
            {problem&&<Notice kind="error">{problem}</Notice>}
            <div><button className="btn btn-primary" disabled={busy==="create"||!online}>{busy==="create"?"Creando…":"Crear documento"}</button></div>
          </form>
        </Panel>
        <Panel title="Importar desde un material" description="Trae el texto adaptado de un material mediante el procesador documental.">
          {ai.data?.document_processor_connected?
            <form className="form" onSubmit={e=>void importFrom(e)}><Field label="Identificador del material"><input value={materialId} onChange={e=>setMaterialId(e.target.value)} className="mono"/></Field><div><button className="btn" disabled={!materialId.trim()||busy==="import"||!online}>Importar</button></div></form>
            :<NotConnected>{ai.loading?"Comprobando el estado del servidor…":ai.error?`No se pudo consultar el estado: ${ai.error.message}`:"El servidor todavía no tiene conectado el procesador documental, por eso la importación está desactivada. Mientras tanto puedes guardar una adaptación como documento desde «Archivos y adaptación»."}</NotConnected>}
        </Panel>
        {error&&<ErrorNotice error={error}/>}
      </div>
      <div>{selected?<Editor key={selected} id={selected} onChanged={docs.reload}/>:<EmptyState title="Selecciona un documento">Elige uno de la lista para editarlo y ver su historial.</EmptyState>}</div>
    </div>
  </>;
}
export default function Documentos(){
  return <><PageHeader title="Documentos editables" description="Edita textos con historial de versiones: cada guardado conserva la versión anterior."/><Gate feature="documents"><Inner/></Gate></>;
}
