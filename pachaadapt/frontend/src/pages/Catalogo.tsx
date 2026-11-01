import {useEffect,useMemo,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {createMaterial,fetchMaterials} from "../services/assignments.service";
import {localDB} from "../offline/local-db";
import {can} from "../lib/permissions";
import {isSafeResourceUrl} from "../lib/format";
import type {LibraryMaterial} from "../lib/types";
import {CachedNotice,EmptyState,ErrorNotice,Field,Loading,Notice,OfflineNotice,PageHeader,Panel,StatusPill} from "../components/ui";

const MIME_SUGGESTIONS=["application/pdf","text/plain","text/html","image/png","image/jpeg","audio/mpeg","video/mp4","application/octet-stream"];

export default function Catalogo(){
  const {profile,online}=useApp();
  const staff=can(profile.role,"library.write");
  const list=useAsync(fetchMaterials,[profile.user,profile.role]);
  const [search,setSearch]=useState("");
  const [local,setLocal]=useState<Set<string>>(new Set());
  const [form,setForm]=useState({title:"",description:"",url:"",mime:"application/octet-stream",status:"published" as "draft"|"published"});
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");const [message,setMessage]=useState("");
  const items=list.data?.data??[];
  // Depende de list.data (referencia estable), no de `items`, que sería un array nuevo en cada render.
  useEffect(()=>{
    let active=true;
    const current=list.data?.data??[];
    Promise.all(current.map(async m=>[m.id,!!(await localDB.getAsset(m.id).catch(()=>undefined))] as const)).then(r=>{if(active)setLocal(new Set(r.filter(x=>x[1]).map(x=>x[0])));});
    return ()=>{active=false;};
  },[list.data]);
  const shown=useMemo(()=>{const q=search.trim().toLocaleLowerCase();return items.filter(m=>!q||m.title.toLocaleLowerCase().includes(q)||m.description.toLocaleLowerCase().includes(q));},[items,search]);

  async function open(m:LibraryMaterial){
    const saved=await localDB.getAsset(m.id).catch(()=>undefined);
    if(saved){const url=URL.createObjectURL(saved);window.open(url,"_blank","noopener");setTimeout(()=>URL.revokeObjectURL(url),60000);return;}
    if(!isSafeResourceUrl(m.resource_url)){setProblem("La dirección de este material no es una URL http(s) ni una ruta local; no se abrirá.");return;}
    if(!online){setProblem("Este material no tiene copia local y no hay conexión para abrirlo.");return;}
    window.open(m.resource_url,"_blank","noopener");
  }
  async function submit(e:React.FormEvent){
    e.preventDefault();setError(null);setMessage("");
    if(!form.title.trim()||!form.url.trim())return setProblem("Completa el título y la dirección del recurso.");
    if(!isSafeResourceUrl(form.url.trim()))return setProblem("La dirección debe ser una URL http(s) o una ruta local que empiece con «/».");
    setProblem("");setBusy(true);
    try{
      await createMaterial({title:form.title.trim(),description:form.description,resource_url:form.url.trim(),mime_type:form.mime.trim()||"application/octet-stream",status:form.status});
      setForm({title:"",description:"",url:"",mime:"application/octet-stream",status:"published"});setMessage("Material registrado en el catálogo.");list.reload();
    }catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  return <>
    <PageHeader title="Catálogo de materiales" description="Recursos de estudio registrados por enlace. Los recursos del mismo servidor se guardan en el dispositivo para usarlos sin conexión." actions={<button className="btn" onClick={list.reload} disabled={list.loading}>{list.loading?"Actualizando…":"Actualizar"}</button>}/>
    {message&&<Notice kind="success">{message}</Notice>}
    {problem&&!staff&&<Notice kind="error">{problem}</Notice>}
    {staff&&<Panel title="Registrar un material" description="Registra un enlace o una ruta local. Para subir archivos PDF/TXT y adaptarlos usa «Archivos y adaptación».">
      <form className="form" onSubmit={e=>void submit(e)} noValidate>
        <div className="grid-2">
          <Field label="Título"><input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} maxLength={200} required/></Field>
          <Field label="Dirección del recurso" hint="URL http(s) o ruta local que empiece con «/»."><input value={form.url} onChange={e=>setForm({...form,url:e.target.value})} maxLength={2048} inputMode="url" required/></Field>
        </div>
        <Field label="Descripción"><textarea rows={2} value={form.description} onChange={e=>setForm({...form,description:e.target.value})} maxLength={5000}/></Field>
        <div className="grid-2">
          <Field label="Tipo de archivo (MIME)"><input list="mimes" value={form.mime} onChange={e=>setForm({...form,mime:e.target.value})} maxLength={150}/><datalist id="mimes">{MIME_SUGGESTIONS.map(m=><option key={m} value={m}/>)}</datalist></Field>
          <Field label="Estado" hint="Los estudiantes solo ven los publicados."><select value={form.status} onChange={e=>setForm({...form,status:e.target.value as "draft"|"published"})}><option value="published">Publicado</option><option value="draft">Borrador</option></select></Field>
        </div>
        {problem&&<Notice kind="error">{problem}</Notice>}{error&&<ErrorNotice error={error}/>}<OfflineNotice what="Registrar materiales"/>
        <div><button className="btn btn-primary" disabled={busy||!online}>{busy?"Guardando…":"Registrar material"}</button></div>
      </form>
    </Panel>}
    {list.data?.fromCache&&<CachedNotice savedAt={list.data.savedAt}/>}
    {list.error&&<ErrorNotice error={list.error} onRetry={list.reload}/>}
    <div className="toolbar"><input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar por título o descripción" aria-label="Buscar materiales"/></div>
    {list.loading&&!list.data?<Loading label="Cargando materiales…"/>:!list.error&&!shown.length?
      <EmptyState title={items.length?"Ningún material coincide":"Todavía no hay materiales"}>{items.length?"Prueba con otro texto.":staff?"Registra el primero con el formulario de arriba.":"Cuando tu docente publique materiales aparecerán aquí."}</EmptyState>:
    <ul className="cards">{shown.map(m=><li className="card" key={m.id}>
      <div className="card-head"><h2>{m.title}</h2>{staff&&<StatusPill status={m.status}/>}</div>
      {m.description&&<p className="prewrap">{m.description}</p>}
      <p className="meta"><span>Tipo: {m.mime_type}</span><span>{local.has(m.id)?"Copia disponible sin conexión":"Sin copia local"}</span></p>
      <div className="row"><button className="btn btn-primary" onClick={()=>void open(m)}>{local.has(m.id)?"Abrir copia local":"Abrir material"}</button></div>
    </li>)}</ul>}
  </>;
}
