import {useEffect,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {getCapabilities,getUploadedMaterial,listMaterials,MATERIAL_ID,uploadMaterial,validateUpload} from "../services/materials.service";
import {loadUploads,upsertUpload} from "../lib/uploadIndex";
import {cacheMaterialList,getCachedMaterialList,materialOfflineState} from "../offline/materials-cache";
import {sha256Hex} from "../lib/hash";
import {connectionNeeds,materialStatusTone,NOT_IMPLEMENTED,offlineSummary,resourceOffline,STATUS_TEXT} from "../lib/materialsView";
import {dateLabel,formatBytes} from "../lib/format";
import type {MaterialInfo} from "../lib/materials.types";
import type {UploadedMaterial} from "../lib/types";
import {MaterialDetail} from "../components/MaterialDetail";
import {CachedNotice,EmptyState,ErrorNotice,Field,Gate,Loading,Notice,OfflineNotice,PageHeader,Panel} from "../components/ui";

/** Ficha mínima desde el índice local de este navegador (lo que ya recordaba fase02). */
function fromIndex(u:UploadedMaterial):MaterialInfo{
  return {id:u.id,filename:u.filename,content_type:u.content_type,size:u.size,sha256:u.sha256,created_at:u.created_at,extracted_at:u.extracted_at,
    status:u.extracted_at?"extracted":"uploaded",method:null,attempts:0,error:null,page_count:null,image_count:null,warnings:[],is_demo:false,adaptation_count:0};
}

async function loadList(user:string):Promise<{data:MaterialInfo[];fromCache:boolean;savedAt?:string}>{
  try{const data=await listMaterials();await cacheMaterialList(user,data).catch(()=>undefined);return {data,fromCache:false};}
  catch(e){
    const status=(e as {status?:number}).status;
    if(!(typeof status==="number"&&status>=400&&status<500)){const c=await getCachedMaterialList(user).catch(()=>undefined);if(c)return {data:c.value,fromCache:true,savedAt:c.saved_at};const known=loadUploads(user);if(known.length)return {data:known.map(fromIndex),fromCache:true};}
    throw e;
  }
}

function Inner(){
  const {profile,online}=useApp();
  const list=useAsync(()=>loadList(profile.user),[profile.user]);
  const caps=useAsync(()=>online?getCapabilities():Promise.reject(new Error("Sin conexión: no se puede consultar qué ofrece el servidor.")),[online]);
  const [selected,setSelected]=useState<string|null>(null);
  const [file,setFile]=useState<File|null>(null);const [inputKey,setInputKey]=useState(0);
  const [lookup,setLookup]=useState("");
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");const [message,setMessage]=useState("");
  const [states,setStates]=useState<Record<string,{detail:boolean;original:boolean}>>({});
  const items=list.data?.data??[];
  useEffect(()=>{let on=true;Promise.all(items.map(async m=>[m.id,await materialOfflineState(profile.user,m.id).catch(()=>({detail:false,original:false}))] as const)).then(r=>on&&setStates(Object.fromEntries(r)));return()=>{on=false;};},[list.data,profile.user]);// eslint-disable-line react-hooks/exhaustive-deps
  const rows=items.map(m=>resourceOffline(states[m.id]??{detail:false,original:false}));
  const current=items.find(m=>m.id===selected)??null;
  const capsData=caps.data??null;

  async function upload(e:React.FormEvent){
    e.preventDefault();setError(null);setMessage("");
    if(!file)return setProblem("Elige un archivo PDF o TXT.");
    const invalid=validateUpload(file);if(invalid)return setProblem(invalid);
    setProblem("");setBusy(true);
    try{
      const localHash=await sha256Hex(file);const meta=await uploadMaterial(file);
      upsertUpload(profile.user,meta);
      setFile(null);setInputKey(k=>k+1);list.reload();setSelected(meta.id);
      setMessage(localHash===null?"Archivo subido. No se pudo calcular la huella local en este navegador.":localHash===meta.sha256?"Archivo subido. La huella SHA-256 coincide: el original se conservó íntegro.":"Archivo subido, pero la huella SHA-256 NO coincide con la de tu archivo. Vuelve a subirlo.");
    }catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  async function find(e:React.FormEvent){
    e.preventDefault();setError(null);setMessage("");
    const id=lookup.trim().toLowerCase();
    if(!MATERIAL_ID.test(id))return setProblem("El identificador tiene 32 caracteres hexadecimales (0-9, a-f).");
    setProblem("");setBusy(true);
    try{const meta=await getUploadedMaterial(id);upsertUpload(profile.user,meta);list.reload();setSelected(meta.id);setLookup("");}
    catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  return <>
    <OfflineNotice what="Subir, extraer y adaptar materiales"/>
    <div className="grid-2 top">
      <Panel title="Subir un archivo" description="PDF o TXT, hasta 25 MB. El servidor conserva el original sin modificarlo.">
        <form className="form" onSubmit={e=>void upload(e)} noValidate>
          <Field label="Archivo"><input key={inputKey} type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={e=>{setFile(e.target.files?.[0]??null);setProblem("");}}/></Field>
          <div><button className="btn btn-primary" disabled={busy||!online||!file}>{busy?"Subiendo…":"Subir archivo"}</button></div>
        </form>
      </Panel>
      <Panel title="Consultar por identificador" description="Abre un material subido antes, incluso desde otro navegador.">
        <form className="form" onSubmit={e=>void find(e)} noValidate>
          <Field label="Identificador del material"><input value={lookup} onChange={e=>setLookup(e.target.value)} className="mono" spellCheck={false} autoComplete="off"/></Field>
          <div><button className="btn" disabled={busy||!online||!lookup.trim()}>Consultar</button></div>
        </form>
      </Panel>
    </div>
    {problem&&<Notice kind="error">{problem}</Notice>}{error&&<ErrorNotice error={error}/>}{message&&<Notice kind="success">{message}</Notice>}
    <Panel title="Mis materiales" description={items.length?offlineSummary(rows):undefined} actions={<button className="btn" onClick={list.reload} disabled={list.loading||!online}>Actualizar</button>}>
      {list.data?.fromCache&&<CachedNotice savedAt={list.data.savedAt}/>}
      {list.error&&<ErrorNotice error={list.error} onRetry={list.reload}/>}
      {list.loading&&!list.data?<Loading label="Cargando materiales…"/>:!list.error&&!items.length?<EmptyState title="Todavía no hay materiales">Sube un archivo, o carga los 3 materiales de demostración con <code>python scripts/import_materials.py</code>.</EmptyState>:
      <ul className="picklist">{items.map((m,i)=><li key={m.id}><button className={`pick ${m.id===selected?"active":""}`} aria-pressed={m.id===selected} onClick={()=>setSelected(m.id)}>
        <strong>{m.filename}{m.is_demo&&" · DEMOSTRACIÓN"}</strong>
        <span className="hint">{formatBytes(m.size)} · {dateLabel(m.created_at)} · <span className={`pill ${materialStatusTone(m.status)==="ok"?"st-ok":materialStatusTone(m.status)==="warn"?"st-config":"submitted"}`}>{STATUS_TEXT[m.status]}</span> · {m.adaptation_count} adaptación(es)</span>
        <span className="hint">{rows[i].level==="full"?"Disponible sin conexión":rows[i].level==="partial"?"Parcialmente disponible sin conexión":"Requiere conexión"}</span>
      </button></li>)}</ul>}
    </Panel>
    {current&&<MaterialDetail key={current.id} material={current} caps={capsData} onUpdated={m=>{list.setData({data:items.map(x=>x.id===m.id?m:x),fromCache:false});}}/>}
    <Panel title="Qué puede hacer este servidor" description="Todo se procesa con reglas locales del servidor, sin IA ni servicios de Internet. Para usarlo desde aquí hace falta conexión con el servidor; sin ella solo se pueden consultar los materiales guardados en este dispositivo.">
      {caps.loading?<Loading/>:caps.error?<Notice kind="warn">{caps.error.message}</Notice>:
      <div className="table-wrap"><table className="data"><caption className="sr-only">Capacidades del servidor</caption><thead><tr><th scope="col">Función</th><th scope="col">Estado</th><th scope="col">Detalle</th></tr></thead>
        <tbody>{connectionNeeds(capsData).map(r=><tr key={r.label}><th scope="row">{r.label}</th><td><span className={`pill ${r.ok?"st-ok":"st-config"}`}>{r.ok?"Disponible":"No disponible"}</span></td><td>{r.ok?(r.needsInternet?"Necesita Internet.":"Local, sin Internet."):r.reason}</td></tr>)}</tbody></table></div>}
      <h3>No implementado</h3>
      <ul className="plain">{NOT_IMPLEMENTED.map(x=><li key={x}>{x}</li>)}</ul>
    </Panel>
  </>;
}
export default function Materiales(){
  return <><PageHeader title="Archivos y adaptación" description="Sube PDF o TXT, obtén su texto organizado y genera adaptaciones accesibles guardadas junto al original."/><Gate feature="materials.upload"><Inner/></Gate></>;
}
