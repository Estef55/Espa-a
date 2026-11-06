import {useCallback,useEffect,useRef,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {adaptMaterial,downloadAudio,downloadOriginal,exportAdaptation,extractMaterial,getMaterialInfo,getMaterialText,linkAdaptation,listAdaptations,reviewAdaptation} from "../services/materials.service";
import {createDocument} from "../services/documents.service";
import {listAdaptations as listLocalAdaptations,saveAdaptation} from "../offline/adaptation-store";
import type {StoredAdaptation} from "../offline/adaptation-store";
import {adaptationToText} from "../lib/quiz";
import {fetchAssignments} from "../services/assignments.service";
import {cacheMaterialDetail,downloadMaterialForOffline,getCachedMaterialDetail,materialOfflineState} from "../offline/materials-cache";
import {adaptationBadge,canGenerate,groupByKind,KIND_HELP,KIND_LABEL,kindAvailability,KINDS,resourceOffline,STATUS_TEXT} from "../lib/materialsView";
import {dateLabel,formatBytes} from "../lib/format";
import type {AdaptationKind,QuizQuestion} from "../lib/types";
import type {AdaptationRecord,Capabilities,ExportFormat,MaterialInfo,OrganizedText} from "../lib/materials.types";
import {CachedNotice,ErrorNotice,Field,Loading,Notice,Panel} from "../components/ui";

const asError=(e:unknown)=>e instanceof Error?e:new Error(String(e));
function save(blob:Blob,filename:string){const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}

/** Convierte una adaptación guardada solo en este dispositivo (almacén de fase02) al formato común de la lista. */
function localToRecord(r:StoredAdaptation):AdaptationRecord{
  const c=(r.content??{}) as Partial<AdaptationRecord>;
  const result=(c.result??"") as AdaptationRecord["result"];
  const text=typeof c.text==="string"?c.text:(typeof result==="string"||Array.isArray(result)?adaptationToText(result as string|QuizQuestion[]):"");
  return {id:null,material_id:r.material_id,adaptation:r.kind as AdaptationKind,status:c.status==="partial"?"partial":"complete",persisted:false,result,text,
    warnings:c.warnings??[],review_required:r.review_required,generated_at:c.generated_at??r.saved_at,links:[]};
}

function AudioPlayer({materialId,adaptationId}:{materialId:string;adaptationId:string}){
  const [url,setUrl]=useState("");const [error,setError]=useState<Error|null>(null);
  useEffect(()=>{let made="";let alive=true;
    downloadAudio(materialId,adaptationId).then(({blob})=>{if(!alive)return;made=URL.createObjectURL(blob);setUrl(made);}).catch(e=>alive&&setError(asError(e)));
    return()=>{alive=false;if(made)URL.revokeObjectURL(made);};
  },[materialId,adaptationId]);
  if(error)return <ErrorNotice error={error}/>;
  return url?<audio controls src={url} aria-label="Audio generado a partir del texto del material"/>:<Loading label="Cargando audio…"/>;
}

function AdaptationCard({a,material,onChanged,online}:{a:AdaptationRecord;material:MaterialInfo;onChanged:()=>void;online:boolean}){
  const [busy,setBusy]=useState("");const [error,setError]=useState<Error|null>(null);const [message,setMessage]=useState("");
  const [open,setOpen]=useState(false);const [target,setTarget]=useState("");
  const assignments=useAsync(()=>open&&online?fetchAssignments():Promise.resolve(undefined),[open,online]);
  const badge=adaptationBadge(a);const id=a.id??"";const onServer=!!a.id;
  const run=async(name:string,job:()=>Promise<void>)=>{setBusy(name);setError(null);setMessage("");try{await job();}catch(e){setError(asError(e));}finally{setBusy("");}};
  const review=()=>run("review",async()=>{await reviewAdaptation(material.id,id,a.review_status!=="approved");onChanged();});
  const exportAs=(f:ExportFormat)=>run("export",async()=>{const {blob,filename}=await exportAdaptation(material.id,id,f);save(blob,filename??`adaptacion.${f}`);setMessage("Archivo descargado. Incluye el aviso de si fue revisado por el docente.");});
  const toDocument=()=>run("doc",async()=>{
    const doc=await createDocument({title:`${KIND_LABEL[a.adaptation]} — ${material.filename}`.slice(0,200),content:a.text,source_material_id:material.id});
    if(onServer){await linkAdaptation(material.id,id,"document",doc.id);onChanged();}
    setMessage(`Guardado como documento editable «${doc.title}»${onServer?" y vinculado a esta adaptación":""}.`);
  });
  const copy=async()=>{try{await navigator.clipboard.writeText(a.text);setMessage("Copiado al portapapeles.");}catch{setError(new Error("El navegador no permitió copiar. Selecciona el texto y cópialo manualmente."));}};
  const toAssignment=()=>run("link",async()=>{if(!target)return;await linkAdaptation(material.id,id,"assignment",target);onChanged();setMessage("Adaptación vinculada a la actividad.");});
  const actions=a.links??[];
  return <li className="card">
    {!onServer&&<Notice kind="info">Esta adaptación solo está guardada en este dispositivo (no se pudo consultar el servidor). Se puede copiar o guardar como documento cuando haya conexión.</Notice>}
    <div className="card-head"><h3>{KIND_LABEL[a.adaptation]}</h3><span className={`pill ${badge.tone==="ok"?"st-ok":badge.tone==="warn"?"st-config":"submitted"}`}>{badge.text}</span></div>
    <p className="meta"><span>Generada: {dateLabel(a.created_at??a.generated_at)}</span><span>Origen del texto: {a.source_origin==="edited"?"texto editado":"texto extraído del original"}</span><span>Original: {material.filename}</span></p>
    {a.status==="partial"&&<Notice kind="warn"><strong>Adaptación parcial.</strong> No se completó todo lo pedido; no la uses como si estuviera completa.</Notice>}
    {(a.warnings?.length??0)>0&&<ul className="plain">{a.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul>}
    {a.adaptation==="audio"&&id?<AudioPlayer materialId={material.id} adaptationId={id}/>:null}
    <details><summary>Ver contenido</summary>
      {a.adaptation==="quiz"&&Array.isArray(a.result)?<ol className="output">{(a.result as {id:number;question:string}[]).map(q=><li key={q.id}><p>{q.question}</p><p className="hint">Pregunta abierta · sin clave de respuesta: la define el docente.</p></li>)}</ol>:<p className="prewrap output">{a.text}</p>}
    </details>
    {actions.length>0&&<p className="hint">Vinculada a: {actions.map(l=>`${l.target_type==="document"?"documento":"actividad"} ${l.target_id.slice(0,8)}…`).join(", ")}</p>}
    <div className="row">
      {onServer&&<button className="btn" onClick={()=>void review()} disabled={!online||!!busy}>{a.review_status==="approved"?"Quitar aprobación":"Marcar como revisada"}</button>}
      {onServer&&<button className="btn" onClick={()=>void exportAs("html")} disabled={!online||!!busy}>Descargar HTML</button>}
      {onServer&&<button className="btn" onClick={()=>void exportAs("txt")} disabled={!online||!!busy}>Descargar TXT</button>}
      {a.adaptation!=="audio"&&a.text&&<button className="btn" onClick={()=>void copy()}>Copiar texto</button>}
      {a.adaptation!=="audio"&&<button className="btn" onClick={()=>void toDocument()} disabled={!online||!!busy}>{busy==="doc"?"Guardando…":"Guardar como documento editable"}</button>}
      {onServer&&<button className="btn btn-quiet" onClick={()=>setOpen(!open)} aria-expanded={open}>Vincular a una actividad</button>}
    </div>
    {open&&onServer&&<div className="row">{!online?<Notice kind="warn">Para vincular hace falta conexión.</Notice>:assignments.loading?<Loading/>:
      <><Field label="Actividad"><select value={target} onChange={e=>setTarget(e.target.value)}><option value="">Elige una actividad…</option>{(assignments.data?.data??[]).map(x=><option key={x.id} value={x.id}>{x.title}</option>)}</select></Field>
      <button className="btn btn-primary" onClick={()=>void toAssignment()} disabled={!target||!!busy}>Vincular</button></>}</div>}
    {message&&<Notice kind="success">{message} {message.startsWith("Guardado como documento")&&<a href="#/documentos">Abrir Documentos</a>}</Notice>}{error&&<ErrorNotice error={error}/>}
  </li>;
}

export function MaterialDetail({material,caps,onUpdated}:{material:MaterialInfo;caps:Capabilities|null;onUpdated:(m:MaterialInfo)=>void}){
  const {profile,online}=useApp();
  const [info,setInfo]=useState(material);
  const [adaptations,setAdaptations]=useState<AdaptationRecord[]>([]);const [text,setText]=useState<OrganizedText|null>(null);
  const [fromCache,setFromCache]=useState<string|undefined>();const [loading,setLoading]=useState(true);
  const [kind,setKind]=useState<AdaptationKind>("summary");const [ocr,setOcr]=useState(false);
  const [draft,setDraft]=useState("");const [useEdited,setUseEdited]=useState(false);const [amount,setAmount]=useState({summary:5,easy_read:22,quiz:5});
  const [busy,setBusy]=useState("");const [error,setError]=useState<Error|null>(null);const [message,setMessage]=useState("");
  const [offline,setOffline]=useState({detail:false,original:false});
  const alive=useRef(true);useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);

  const refreshOffline=useCallback(()=>materialOfflineState(profile.user,material.id).then(s=>alive.current&&setOffline(s)).catch(()=>undefined),[profile.user,material.id]);
  const load=useCallback(async()=>{
    setLoading(true);setError(null);
    try{
      const m=await getMaterialInfo(material.id);const list=await listAdaptations(material.id);
      const t=m.status==="extracted"||m.status==="no_text"?await getMaterialText(material.id).catch(()=>null):null;
      if(!alive.current)return;
      setInfo(m);onUpdated(m);setAdaptations(list);setText(t);setFromCache(undefined);
      if((await materialOfflineState(profile.user,material.id)).detail)await cacheMaterialDetail(profile.user,{material:m,adaptations:list,text:t}); // mantiene al día la copia ya guardada
    }catch(e){
      const status=(e as {status?:number}).status;const unreachable=!(typeof status==="number"&&status>=400&&status<500);
      const cached=unreachable?await getCachedMaterialDetail(profile.user,material.id).catch(()=>undefined):undefined;
      if(cached){if(alive.current){setInfo(cached.value.material);setAdaptations(cached.value.adaptations);setText(cached.value.text);setFromCache(cached.saved_at);}}
      else{
        const local=unreachable?await listLocalAdaptations(profile.user,material.id).catch(()=>[] as StoredAdaptation[]):[];
        if(!alive.current)return;
        if(local.length){setAdaptations(local.map(localToRecord));setFromCache(local.map(l=>l.saved_at).sort().pop());}
        else setError(asError(e));
      }
    }finally{if(alive.current)setLoading(false);refreshOffline();}
  },[material.id,profile.user]);// eslint-disable-line react-hooks/exhaustive-deps
  useEffect(()=>{void load();},[load]);

  const run=async(name:string,job:()=>Promise<void>)=>{setBusy(name);setError(null);setMessage("");try{await job();}catch(e){setError(asError(e));await load();}finally{if(alive.current)setBusy("");}};
  const extract=()=>run("extract",async()=>{const r=await extractMaterial(info.id,ocr);setDraft(r.text);setUseEdited(false);setMessage(r.characters?`Se extrajeron ${r.characters.toLocaleString("es-PE")} caracteres${r.ocr_used?" con OCR":""}.`:"No se encontró texto en el documento.");await load();});
  const generate=()=>run("adapt",async()=>{
    const options=kind==="summary"?{max_sentences:amount.summary}:kind==="easy_read"?{max_words:amount.easy_read}:kind==="quiz"?{count:amount.quiz}:{};
    const a=await adaptMaterial(info.id,kind,{...options,ocr,...(useEdited&&draft.trim()?{text:draft}:{})});
    if(!(a.persisted===false||a.status==="empty"))await saveAdaptation(profile.user,info.id,kind,a,a.review_required).catch(()=>undefined); // copia en este dispositivo
    setMessage(a.persisted===false||a.status==="empty"?`No se generó «${KIND_LABEL[kind]}»: ${a.warnings?.[0]??"el texto no alcanza para este tipo de adaptación."} No se guardó nada.`:`«${KIND_LABEL[kind]}» generada y guardada. Quedó pendiente de revisión docente.`);
    await load();
  });
  const original=()=>run("orig",async()=>{const {blob,filename}=await downloadOriginal(info.id);save(blob,filename??info.filename);});
  const keep=()=>run("keep",async()=>{
    const r=await downloadMaterialForOffline(profile.user,info.id,{
      detail:async()=>{const m=await getMaterialInfo(info.id);const list=await listAdaptations(info.id);const t=m.status==="extracted"||m.status==="no_text"?await getMaterialText(info.id).catch(()=>null):null;return {material:m,adaptations:list,text:t};},
      original:async()=>(await downloadOriginal(info.id)).blob,
    });
    await refreshOffline();
    if(r.errors.length)throw new Error(`Guardado incompleto. ${r.errors.join(" ")}`);
    setMessage("Material guardado en este dispositivo: podrás consultar sus datos y adaptaciones sin conexión.");
  });

  const blocked=canGenerate(info);const av=kindAvailability(caps,kind);const off=resourceOffline(offline);
  return <div className="stack">
    <Panel title={info.filename} actions={<button className="btn" onClick={()=>void load()} disabled={!online||loading}>Actualizar</button>}>
      {fromCache&&<CachedNotice savedAt={fromCache}/>}
      {info.is_demo&&<Notice kind="info"><strong>Material de demostración.</strong> No es un material curricular oficial.</Notice>}
      <dl className="kv">
        <dt>Estado</dt><dd>{STATUS_TEXT[info.status]}{info.method?` (${info.method})`:""}</dd>
        <dt>Tipo y tamaño</dt><dd>{info.content_type} · {formatBytes(info.size)}{info.page_count?` · ${info.page_count} pág.`:""}{info.image_count?` · ${info.image_count} imagen(es)`:""}</dd>
        <dt>Subido</dt><dd>{dateLabel(info.created_at)}</dd><dt>Texto extraído</dt><dd>{info.extracted_at?dateLabel(info.extracted_at):"Aún no"}</dd>
        <dt>Intentos de extracción</dt><dd>{info.attempts}</dd>
        <dt>SHA-256</dt><dd className="mono" title={info.sha256}>{info.sha256}</dd>
        <dt>Identificador</dt><dd className="mono">{info.id}</dd>
      </dl>
      {info.error&&<Notice kind="error"><strong>No se pudo procesar.</strong> {info.error.message} <em>({info.error.code})</em></Notice>}
      {info.warnings.length>0&&<Notice kind="warn"><ul className="plain">{info.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></Notice>}
      <div className="row">
        <button className="btn" onClick={()=>void original()} disabled={!online||!!busy}>Descargar el original</button>
        <button className="btn" onClick={()=>void keep()} disabled={!online||!!busy}>{busy==="keep"?"Guardando…":"Guardar para usar sin conexión"}</button>
      </div>
      <p className="hint">El servidor conserva el original sin modificarlo; «Descargar el original» lo baja tal como se subió.</p>
      <p className="hint" role="status">{off.text}</p>
    </Panel>

    <Panel title="Texto del material" description="Se lee con reglas locales; nada se envía a servicios externos.">
      <label className="check"><input type="checkbox" checked={ocr} onChange={e=>setOcr(e.target.checked)} disabled={!caps?.features?.ocr?.available}/> Usar OCR si el PDF es una imagen escaneada {!caps?.features?.ocr?.available&&<span className="hint">(no disponible: {caps?.features?.ocr?.reason??"sin información del servidor"})</span>}</label>
      <div><button className="btn btn-primary" onClick={()=>void extract()} disabled={!online||!!busy}>{busy==="extract"?"Extrayendo…":info.status==="uploaded"?"Extraer texto":"Volver a extraer"}</button></div>
      {loading&&!text?<Loading/>:text?.organized.blocks.length?<div className="organized" tabIndex={0} aria-label="Texto organizado del material">
        {text.organized.blocks.map((b,i)=>b.type==="heading"?<h3 key={i}>{b.text}</h3>:b.type==="notice"?<p key={i} className="hint">{b.text}</p>:b.type==="list"?<ul key={i} className="plain">{b.text.split("\n").map((l,j)=><li key={j}>{l.replace(/^[-•*]\s*/,"")}</li>)}</ul>:<p key={i} className="prewrap">{b.text}</p>)}
      </div>:info.status==="extracted"?<Notice kind="warn">El texto está vacío.</Notice>:null}
      {text?.organized.warnings?.map((w,i)=><p className="hint" key={i}>{w}</p>)}
      {draft&&<details><summary>Corregir el texto antes de adaptar ({draft.length.toLocaleString("es-PE")} caracteres)</summary>
        <Field label="Texto extraído (editable)" hint="Puedes corregirlo aquí; solo se usará para adaptar si marcas la opción de «Generar adaptación»."><textarea rows={8} value={draft} onChange={e=>setDraft(e.target.value)}/></Field></details>}
    </Panel>

    <Panel title="Generar adaptación" description="Cada adaptación se guarda en el servidor, queda enlazada a este original y requiere revisión docente.">
      <Field label="Tipo de adaptación"><select value={kind} onChange={e=>setKind(e.target.value as AdaptationKind)}>
        {KINDS.map(k=>{const a=kindAvailability(caps,k);return <option key={k} value={k}>{KIND_LABEL[k]}{a.available?"":" — no disponible"}</option>;})}</select></Field>
      <p className="hint">{KIND_HELP[kind]}</p>
      <div className="grid-2">
        {kind==="summary"&&<Field label="Máximo de oraciones"><input type="number" min={1} max={20} value={amount.summary} onChange={e=>setAmount({...amount,summary:Math.min(20,Math.max(1,Number(e.target.value)||1))})}/></Field>}
        {kind==="easy_read"&&<Field label="Máximo de palabras por oración"><input type="number" min={5} max={60} value={amount.easy_read} onChange={e=>setAmount({...amount,easy_read:Math.min(60,Math.max(5,Number(e.target.value)||5))})}/></Field>}
        {kind==="quiz"&&<Field label="Cantidad de preguntas"><input type="number" min={1} max={20} value={amount.quiz} onChange={e=>setAmount({...amount,quiz:Math.min(20,Math.max(1,Number(e.target.value)||1))})}/></Field>}
      </div>
      {draft&&<label className="check"><input type="checkbox" checked={useEdited} onChange={e=>setUseEdited(e.target.checked)}/> Adaptar el texto corregido de arriba (incluye mis correcciones)</label>}
      {!av.available&&<Notice kind="warn"><strong>No disponible.</strong> {av.reason}</Notice>}
      {blocked&&<Notice kind="info">{blocked}</Notice>}
      <div><button className="btn btn-primary" onClick={()=>void generate()} disabled={!online||!!busy||!av.available||!!blocked}>{busy==="adapt"?"Generando…":"Generar adaptación"}</button></div>
    </Panel>

    <Panel title={`Adaptaciones de este material (${adaptations.length})`}>
      {loading&&!adaptations.length?<Loading/>:!adaptations.length?<p className="hint">Todavía no hay adaptaciones guardadas.</p>:
      groupByKind(adaptations).map(g=><section key={g.kind}><h3>{KIND_LABEL[g.kind]}</h3><ul className="cards">{g.items.map(a=><AdaptationCard key={a.id??`local-${a.adaptation}`} a={a} material={info} online={online} onChanged={()=>void load()}/>)}</ul></section>)}
    </Panel>
    {message&&<Notice kind="success">{message}</Notice>}{error&&<ErrorNotice error={error}/>}
  </div>;
}
