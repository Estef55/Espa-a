import {useEffect,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {archiveDocument,createDocument,getDocument,getVersion,importDocument,listDocuments,listVersions,restoreVersion,saveDocument} from "../services/documents.service";
import {clearDocumentDraft,getDocumentDraft,saveDocumentDraft,saveDocumentList,getDocumentList,saveDocumentSnapshot,getDocumentSnapshot} from "../offline/adaptation-store";
import {dateLabel} from "../lib/format";
import type {DocumentFull,DocumentSummary,DocumentVersionFull} from "../lib/types";
import {EmptyState,ErrorNotice,Field,Gate,Loading,Notice,NotConnected,OfflineNotice,PageHeader,Panel} from "../components/ui";

const asError=(e:unknown)=>e instanceof Error?e:new Error(String(e));

function Editor({id,onChanged}:{id:string;onChanged:()=>void}){
  const {online,profile,epoch}=useApp();
  const doc=useAsync(()=>getDocument(id),[id,profile.user,epoch]);
  const versions=useAsync(()=>listVersions(id),[id,profile.user,epoch]);
  const [content,setContent]=useState("");const [base,setBase]=useState(1);const [reason,setReason]=useState("");
  const [viewing,setViewing]=useState<DocumentVersionFull|null>(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [message,setMessage]=useState("");
  const [draftReady,setDraftReady]=useState(false);const [localDraftSaved,setLocalDraftSaved]=useState(false);const [draftError,setDraftError]=useState<Error|null>(null);
  const [cachedDoc,setCachedDoc]=useState<DocumentFull|null>(null);const [usingLocalSnapshot,setUsingLocalSnapshot]=useState(false);
  const [remoteConflict,setRemoteConflict]=useState<DocumentFull|null>(null);
  const sourceDoc=doc.data??cachedDoc;
  useEffect(()=>{
    if(!sourceDoc)return;
    let active=true;
    if(doc.data){setCachedDoc(doc.data);setUsingLocalSnapshot(false);void saveDocumentSnapshot(profile.user,id,doc.data).catch(e=>setDraftError(asError(e)));}
    else setUsingLocalSnapshot(true);
    setDraftReady(false);setContent(sourceDoc.content);setBase(sourceDoc.current_version);setRemoteConflict(null);
    void getDocumentDraft(profile.user,id).then(draft=>{
      if(!active)return;
      if(draft){setContent(draft.content);setBase(draft.base_version);setLocalDraftSaved(true);
        if(draft.base_version!==sourceDoc.current_version){setRemoteConflict(sourceDoc);setMessage(`Se recuperó un borrador local basado en v${draft.base_version}; la última versión guardada disponible es v${sourceDoc.current_version}.`);}
        else setMessage("Se recuperó un borrador local pendiente de guardar en el servidor.");
      }else setLocalDraftSaved(false);
      setDraftReady(true);
    }).catch(e=>{if(active){setDraftError(asError(e));setDraftReady(true);}});
    return()=>{active=false;};
  },[sourceDoc,id,profile.user]);
  useEffect(()=>{
    if(doc.data||cachedDoc)return;
    const kind=(doc.error as {kind?:string}|undefined)?.kind;
    if(online&&kind!=="network")return;
    let active=true;
    void getDocumentSnapshot<DocumentFull>(profile.user,id).then(snapshot=>{
      if(active&&snapshot){setCachedDoc(snapshot);setUsingLocalSnapshot(true);}
    }).catch(e=>{if(active)setDraftError(asError(e));});
    return()=>{active=false;};
  },[doc.data,doc.error,cachedDoc,online,profile.user,id,epoch]);
  const current=sourceDoc;
  useEffect(()=>{
    if(!draftReady||!current)return;
    const timer=window.setTimeout(()=>{
      if(content===current.content){void clearDocumentDraft(profile.user,id).then(()=>setLocalDraftSaved(false)).catch(e=>setDraftError(asError(e)));return;}
      void saveDocumentDraft(profile.user,id,content,base).then(()=>{setLocalDraftSaved(true);setDraftError(null);}).catch(e=>setDraftError(asError(e)));
    },250);
    return()=>window.clearTimeout(timer);
  },[draftReady,profile.user,id,content,base,current]);
  const dirty=!!current&&content!==current.content;const archived=!!current?.archived;

  async function act(job:()=>Promise<void>){setBusy(true);setError(null);setMessage("");try{await job();}catch(e){setError(asError(e));}finally{setBusy(false);}}
  const save=()=>act(async()=>{
    try{
      const saved=await saveDocument(id,content,base,reason.trim()||undefined);
      await clearDocumentDraft(profile.user,id);setLocalDraftSaved(false);setRemoteConflict(null);
      setContent(saved.content);setBase(saved.current_version);doc.setData(saved);setReason("");
      setMessage(`Guardado en el servidor como versión ${saved.current_version}.`);versions.reload();onChanged();
    }catch(e){
      if((e as {kind?:string})?.kind==="conflict")try{setRemoteConflict(await getDocument(id));}catch{/* conserva el error original */}
      throw e;
    }
  });
  const openVersion=(v:number)=>act(async()=>setViewing(await getVersion(id,v)));
  const restore=()=>act(async()=>{
    if(!viewing)return;
    if(dirty&&!window.confirm("Tienes cambios sin guardar que se perderán al restaurar. ¿Continuar?"))return;
    const restored=await restoreVersion(id,viewing.version,base,`Restaurada desde la versión ${viewing.version}`);
    await clearDocumentDraft(profile.user,id);setLocalDraftSaved(false);setRemoteConflict(null);
    doc.setData(restored);setContent(restored.content);setBase(restored.current_version);setViewing(null);setMessage(`Versión ${viewing.version} restaurada como versión ${restored.current_version}.`);versions.reload();onChanged();
  });
  const archive=()=>act(async()=>{
    if(!window.confirm("¿Archivar este documento? No se borra, pero ya no se podrá editar."))return;
    await archiveDocument(id);setMessage("Documento archivado.");doc.reload();onChanged();
  });
  async function keepLocalAgainstLatest(){
    const latest=remoteConflict;if(!latest||!doc.data||latest.archived)return;
    try{await saveDocumentDraft(profile.user,id,content,latest.current_version);}
    catch(e){setDraftError(asError(e));return;}
    setLocalDraftSaved(true);setCachedDoc(latest);doc.setData(latest);setBase(latest.current_version);setRemoteConflict(null);
    setMessage(`Revisaste la versión del servidor v${latest.current_version}. Tu borrador local sigue pendiente; guárdalo para crear una nueva versión.`);
  }
  async function useLatestFromServer(){
    const latest=remoteConflict;if(!latest||!doc.data)return;
    try{await clearDocumentDraft(profile.user,id);}
    catch(e){setDraftError(asError(e));return;}
    setContent(latest.content);setBase(latest.current_version);setCachedDoc(latest);doc.setData(latest);setLocalDraftSaved(false);setRemoteConflict(null);
    setMessage(`Se cargó la versión del servidor v${latest.current_version}; el borrador local se descartó.`);
  }
  function discardChanges(){
    if(!current)return;
    setContent(current.content);setBase(current.current_version);setRemoteConflict(null);
    void clearDocumentDraft(profile.user,id).then(()=>setLocalDraftSaved(false)).catch(e=>setDraftError(asError(e)));
    setMessage("Cambios locales descartados.");
  }
  if(doc.loading&&!current)return <Loading label="Cargando documento…"/>;
  if(!current&&doc.error)return <ErrorNotice error={doc.error} onRetry={doc.reload}/>;
  if(!current)return null;
  return <div className="stack">
    <Panel title={current.title} description={`Versión ${current.current_version} · actualizado ${dateLabel(current.updated_at)}${current.source_material_id?` · origen: material ${current.source_material_id}`:""}`}
      actions={!archived&&<button type="button" className="btn btn-quiet" onClick={()=>void archive()} disabled={busy||!online||!doc.data||dirty||localDraftSaved||!!remoteConflict}>Archivar</button>}>
      {usingLocalSnapshot&&<Notice kind="warn">Documento cargado desde la última copia local. No se confirma la versión actual del servidor hasta recuperar conexión.</Notice>}
      {archived&&<Notice kind="info">Documento archivado: se conserva su historial, pero no admite cambios.</Notice>}
      <Field label="Contenido" hint={!draftReady?"Recuperando borrador local…":`${content.length.toLocaleString("es-PE")} caracteres${dirty?" · cambios sin guardar":""}`}><textarea rows={14} value={content} onChange={e=>setContent(e.target.value)} readOnly={archived||!draftReady}/></Field>
      {!archived&&<><Field label="Motivo del cambio (opcional)" hint="Queda registrado en el historial."><input value={reason} onChange={e=>setReason(e.target.value)} maxLength={500} disabled={!draftReady}/></Field>
      <div className="row"><button type="button" className="btn btn-primary" onClick={()=>void save()} disabled={busy||!draftReady||!doc.data||!dirty||!online||!!remoteConflict}>{busy?"Guardando…":"Guardar nueva versión"}</button><button type="button" className="btn btn-quiet" onClick={discardChanges} disabled={!dirty||busy}>Descartar cambios</button></div></>}
      <OfflineNotice what="Guardar documentos"/>
      {localDraftSaved&&dirty&&<Notice kind="warn">Borrador guardado solo en este dispositivo; aún no está en el servidor ni sincronizado. Al recuperar conexión, revisa el borrador y pulsa «Guardar nueva versión».</Notice>}
      {draftError&&<ErrorNotice error={draftError}/>}
      {message&&<Notice kind="success">{message}</Notice>}
      {error&&<ErrorNotice error={error}/>}
      {remoteConflict&&<div className="result" role="alert">
        <h3>Conflicto de versión: el servidor está en v{remoteConflict.current_version}</h3>
        <p>Tu contenido local sigue en el editor. Compáralo con la versión del servidor antes de elegir. No se sobrescribió ninguno de los dos.</p>
        <pre className="output">{remoteConflict.content}</pre>
        {remoteConflict.archived&&<Notice kind="warn">El documento fue archivado en el servidor; no se puede guardar una edición local.</Notice>}
        <div className="row"><button type="button" className="btn btn-primary" onClick={keepLocalAgainstLatest} disabled={remoteConflict.archived}>Conservar mi borrador para una nueva versión</button><button type="button" className="btn btn-quiet" onClick={useLatestFromServer}>Descartar mi borrador y usar v{remoteConflict.current_version}</button></div>
      </div>}
    </Panel>
    <Panel title="Historial de versiones" description="Cada guardado crea una versión nueva; restaurar tampoco borra nada.">
      {versions.loading&&!versions.data?<Loading/>:versions.error?<ErrorNotice error={versions.error} onRetry={versions.reload}/>:
      <div className="table-wrap"><table className="data"><caption className="sr-only">Versiones del documento</caption>
        <thead><tr><th scope="col">Versión</th><th scope="col">Fecha</th><th scope="col">Autor</th><th scope="col">Motivo</th><th scope="col">Tamaño</th><th scope="col"><span className="sr-only">Acciones</span></th></tr></thead>
        <tbody>{(versions.data??[]).map(v=><tr key={v.version}><th scope="row">{v.version}{v.version===current.current_version&&<span className="hint"> (actual)</span>}</th><td>{dateLabel(v.created_at)}</td><td>{v.author_id}</td><td>{v.reason||"—"}{v.restored_from?` (desde v${v.restored_from})`:""}</td><td>{v.size.toLocaleString("es-PE")}</td><td><button className="btn btn-quiet" onClick={()=>void openVersion(v.version)} disabled={busy||!online}>Ver</button></td></tr>)}</tbody></table></div>}
      {viewing&&<div className="result"><h3>Versión {viewing.version}</h3><pre className="output">{viewing.content}</pre>
        <div className="row">{!archived&&viewing.version!==current.current_version&&<button className="btn btn-primary" onClick={()=>void restore()} disabled={busy||!online||!doc.data||!!remoteConflict}>Restaurar esta versión</button>}<button className="btn btn-quiet" onClick={()=>setViewing(null)}>Cerrar</button></div></div>}
    </Panel>
  </div>;
}

function Inner(){
  const {ai,online,profile,epoch}=useApp();
  const [showArchived,setShowArchived]=useState(false);
  const docs=useAsync(()=>listDocuments(showArchived),[showArchived,profile.user,epoch]);
  const [cachedList,setCachedList]=useState<{user:string;includeArchived:boolean;items:DocumentSummary[]}|null>(null);
  useEffect(()=>{
    let active=true;
    if(docs.data){
      const items=docs.data;setCachedList({user:profile.user,includeArchived:showArchived,items});
      void saveDocumentList(profile.user,showArchived,items).catch(()=>undefined);
    }else{
      const kind=(docs.error as {kind?:string}|undefined)?.kind;
      if(!online||kind==="network")void getDocumentList<DocumentSummary>(profile.user,showArchived).then(items=>{
        if(active&&items)setCachedList({user:profile.user,includeArchived:showArchived,items});
      }).catch(()=>undefined);
    }
    return()=>{active=false;};
  },[docs.data,docs.error,profile.user,showArchived,online]);
  const cachedItems=cachedList?.user===profile.user&&cachedList.includeArchived===showArchived?cachedList.items:undefined;
  const canUseCache=!online||(docs.error as {kind?:string}|undefined)?.kind==="network";
  const displayDocs=docs.data??(canUseCache?cachedItems:undefined);
  const listFromCache=!docs.data&&canUseCache&&!!cachedItems;
  const [selected,setSelected]=useState<string|null>(null);
  useEffect(()=>{setSelected(null);},[profile.user]);
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
          {listFromCache&&<Notice kind="warn">Lista local del perfil actual; el servidor no se ha podido consultar. Los cambios quedan solo en este dispositivo hasta guardarlos con conexión.</Notice>}
          {docs.loading&&!displayDocs?<Loading/>:docs.error&&!displayDocs?<ErrorNotice error={docs.error} onRetry={docs.reload}/>:!displayDocs?.length?<EmptyState title="Todavía no hay documentos">Crea uno nuevo o guarda una adaptación desde «Archivos y adaptación».</EmptyState>:
          <ul className="picklist">{displayDocs.map(d=><li key={d.id}><button className={`pick ${d.id===selected?"active":""}`} aria-pressed={d.id===selected} onClick={()=>setSelected(d.id)}><strong>{d.title}</strong><span className="hint">v{d.current_version} · {dateLabel(d.updated_at)}{d.archived?" · archivado":""}</span></button></li>)}</ul>}
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
      <div>{selected?<Editor key={`${profile.user}:${selected}`} id={selected} onChanged={docs.reload}/>:<EmptyState title="Selecciona un documento">Elige uno de la lista para editarlo y ver su historial.</EmptyState>}</div>
    </div>
  </>;
}
export default function Documentos(){
  return <><PageHeader title="Documentos editables" description="Edita textos con historial de versiones: cada guardado conserva la versión anterior."/><Gate feature="documents"><Inner/></Gate></>;
}
