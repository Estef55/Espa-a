import {useEffect,useState} from "react";
import {useApp} from "../context";
import {adaptMaterial,extractMaterial,getUploadedMaterial,MATERIAL_ID,uploadMaterial,validateUpload} from "../services/materials.service";
import {createDocument} from "../services/documents.service";
import {loadUploads,removeUpload,upsertUpload} from "../lib/uploadIndex";
import {sha256Hex} from "../lib/hash";
import {getAdaptation,saveAdaptation} from "../offline/adaptation-store";
import {ADAPTATION_LABEL,adaptationToText} from "../lib/quiz";
import {dateLabel,formatBytes} from "../lib/format";
import type {AdaptationKind,AdaptationResult,ExtractionResult,UploadedMaterial} from "../lib/types";
import {EmptyState,ErrorNotice,Field,Gate,Notice,OfflineNotice,PageHeader,Panel} from "../components/ui";

const asError=(e:unknown)=>e instanceof Error?e:new Error(String(e));

function Detail({material,onUpdated,onRemove}:{material:UploadedMaterial;onUpdated:(m:UploadedMaterial)=>void;onRemove:()=>void}){
  const {online,profile}=useApp();
  const [ocr,setOcr]=useState(false);
  const [extracted,setExtracted]=useState<ExtractionResult|null>(null);const [text,setText]=useState("");
  const [kind,setKind]=useState<AdaptationKind>("summary");const [amount,setAmount]=useState({summary:5,easy_read:22,quiz:5});const [useEdited,setUseEdited]=useState(false);
  const [adapted,setAdapted]=useState<AdaptationResult|null>(null);
  useEffect(()=>{let active=true;setAdapted(null);void getAdaptation(profile.user,material.id,kind).then(record=>{if(active&&record)setAdapted(record.content as AdaptationResult);}).catch(()=>undefined);return()=>{active=false;};},[profile.user,material.id,kind]);
  const [busy,setBusy]=useState<""|"refresh"|"extract"|"adapt"|"save">("");const [error,setError]=useState<Error|null>(null);const [message,setMessage]=useState("");

  async function run(name:typeof busy,job:()=>Promise<void>){setBusy(name);setError(null);setMessage("");try{await job();}catch(e){setError(asError(e));}finally{setBusy("");}}
  const refresh=()=>run("refresh",async()=>{onUpdated(await getUploadedMaterial(material.id));setMessage("Datos actualizados desde el servidor.");});
  const extract=()=>run("extract",async()=>{
    const r=await extractMaterial(material.id,ocr);setExtracted(r);setText(r.text);
    getUploadedMaterial(material.id).then(onUpdated).catch(()=>undefined); // trae la fecha de extracción registrada por el servidor
    setMessage(r.characters?`Se extrajeron ${r.characters.toLocaleString("es-PE")} caracteres${r.ocr_used?" con OCR":""}.`:"");
  });
  const adapt=()=>run("adapt",async()=>{
    const options=kind==="summary"?{max_sentences:amount.summary}:kind==="easy_read"?{max_words:amount.easy_read}:{count:amount.quiz};
    const result=await adaptMaterial(material.id,kind,{...options,ocr,...(useEdited&&text.trim()?{text}:{})});
    await saveAdaptation(profile.user,material.id,kind,result,result.review_required);
    setAdapted(result);
  });
  const saveAsDocument=()=>run("save",async()=>{
    if(!adapted)return;
    const doc=await createDocument({title:`${ADAPTATION_LABEL[adapted.adaptation]} — ${material.filename}`.slice(0,200),content:adaptationToText(adapted.result),source_material_id:material.id});
    setMessage(`Guardado como documento «${doc.title}».`);
  });
  async function copy(){try{await navigator.clipboard.writeText(adapted?adaptationToText(adapted.result):"");setMessage("Copiado al portapapeles.");}catch{setError(new Error("El navegador no permitió copiar. Selecciona el texto y cópialo manualmente."));}}
  const adaptedText=adapted?adaptationToText(adapted.result):"";

  return <div className="stack">
    <Panel title={material.filename} actions={<><button className="btn" onClick={()=>void refresh()} disabled={!online||!!busy}>{busy==="refresh"?"Actualizando…":"Actualizar datos"}</button><button className="btn btn-quiet" onClick={onRemove} title="Solo quita el elemento de la lista de este navegador; no borra nada en el servidor">Quitar de la lista</button></>}>
      <dl className="kv">
        <dt>Tipo</dt><dd>{material.content_type}</dd><dt>Tamaño</dt><dd>{formatBytes(material.size)}</dd>
        <dt>Subido</dt><dd>{dateLabel(material.created_at)}</dd><dt>Texto extraído</dt><dd>{material.extracted_at?dateLabel(material.extracted_at):"Aún no"}</dd>
        <dt>SHA-256</dt><dd className="mono" title={material.sha256}>{material.sha256}</dd>
        <dt>Identificador</dt><dd className="mono">{material.id}</dd>
      </dl>
      <p className="hint">El servidor conserva el archivo original sin modificarlo. La API no ofrece descarga del original, por lo que desde aquí solo se pueden consultar sus datos y la huella SHA-256.</p>
    </Panel>
    <Panel title="Extraer texto" description="Lee el texto del PDF o TXT. El resultado se guarda en el servidor.">
      <label className="check"><input type="checkbox" checked={ocr} onChange={e=>setOcr(e.target.checked)}/> Usar OCR si el PDF es una imagen escaneada <span className="hint">(requiere Tesseract y Poppler en el servidor)</span></label>
      <div><button className="btn btn-primary" onClick={()=>void extract()} disabled={!online||!!busy}>{busy==="extract"?"Extrayendo…":"Extraer texto"}</button></div>
      {extracted&&extracted.characters===0&&<Notice kind="warn">No se encontró texto. Si el PDF es escaneado, activa OCR y vuelve a extraer.</Notice>}
      {extracted&&<Field label={`Texto extraído (${extracted.characters.toLocaleString("es-PE")} caracteres${extracted.ocr_used?", con OCR":""})`} hint="Puedes corregirlo aquí; solo se usará para adaptar si marcas la opción correspondiente."><textarea rows={8} value={text} onChange={e=>setText(e.target.value)}/></Field>}
    </Panel>
    <Panel title="Adaptar contenido" description="Genera una versión adaptada del texto. Si aún no extrajiste el texto, el servidor lo extrae al adaptar.">
      <div className="grid-2">
        <Field label="Tipo de adaptación"><select value={kind} onChange={e=>setKind(e.target.value as AdaptationKind)}><option value="summary">Resumen</option><option value="easy_read">Lectura fácil</option><option value="quiz">Preguntas de comprensión</option></select></Field>
        {kind==="summary"&&<Field label="Máximo de oraciones"><input type="number" min={1} max={20} value={amount.summary} onChange={e=>setAmount({...amount,summary:Math.min(20,Math.max(1,Number(e.target.value)||1))})}/></Field>}
        {kind==="easy_read"&&<Field label="Máximo de palabras por oración"><input type="number" min={5} max={60} value={amount.easy_read} onChange={e=>setAmount({...amount,easy_read:Math.min(60,Math.max(5,Number(e.target.value)||5))})}/></Field>}
        {kind==="quiz"&&<Field label="Cantidad de preguntas"><input type="number" min={1} max={20} value={amount.quiz} onChange={e=>setAmount({...amount,quiz:Math.min(20,Math.max(1,Number(e.target.value)||1))})}/></Field>}
      </div>
      {extracted&&<label className="check"><input type="checkbox" checked={useEdited} onChange={e=>setUseEdited(e.target.checked)}/> Adaptar el texto del cuadro de arriba (incluye mis correcciones)</label>}
      <div><button className="btn btn-primary" onClick={()=>void adapt()} disabled={!online||!!busy}>{busy==="adapt"?"Generando…":"Generar adaptación"}</button></div>
      {adapted&&<div className="result">
        <h3>{ADAPTATION_LABEL[adapted.adaptation]}</h3>
        {adapted.review_required&&<Notice kind="warn"><strong>Revisión docente necesaria.</strong> Este contenido se generó automáticamente con reglas simples; revísalo antes de usarlo con estudiantes.</Notice>}
        {adapted.result===""||(Array.isArray(adapted.result)&&!adapted.result.length)?<Notice kind="warn">La adaptación quedó vacía: el texto es demasiado corto para este tipo de adaptación.</Notice>
          :typeof adapted.result==="string"?<p className="prewrap output">{adapted.result}</p>
          :<ol className="output">{adapted.result.map(q=><li key={q.id}><p>{q.question}</p><p className="hint">Pregunta abierta · {q.teacher_review_required?"requiere revisión docente":""}{q.answer_key===null?" · sin clave de respuesta":""}</p></li>)}</ol>}
        <p className="meta"><span>Generado: {dateLabel(adapted.generated_at)}</span></p>
        {adaptedText&&<div className="row"><button className="btn" onClick={()=>void copy()}>Copiar texto</button><button className="btn btn-primary" onClick={()=>void saveAsDocument()} disabled={!online||!!busy}>{busy==="save"?"Guardando…":"Guardar como documento editable"}</button></div>}
      </div>}
    </Panel>
    {message&&<Notice kind="success">{message} {message.startsWith("Guardado como documento")&&<a href="#/documentos">Abrir Documentos</a>}</Notice>}
    {error&&<ErrorNotice error={error}/>}
  </div>;
}

function Inner(){
  const {profile,online}=useApp();
  const [items,setItems]=useState(()=>loadUploads(profile.user));
  const [selected,setSelected]=useState<string|null>(null);
  const [file,setFile]=useState<File|null>(null);const [inputKey,setInputKey]=useState(0);
  const [lookup,setLookup]=useState("");
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");const [message,setMessage]=useState("");
  const current=items.find(i=>i.id===selected)??null;
  const remember=(m:UploadedMaterial)=>setItems(upsertUpload(profile.user,m));

  async function upload(e:React.FormEvent){
    e.preventDefault();setError(null);setMessage("");
    if(!file)return setProblem("Elige un archivo PDF o TXT.");
    const invalid=validateUpload(file);if(invalid)return setProblem(invalid);
    setProblem("");setBusy(true);
    try{
      const localHash=await sha256Hex(file);
      const meta=await uploadMaterial(file);
      remember(meta);setSelected(meta.id);setFile(null);setInputKey(k=>k+1);
      setMessage(localHash===null?"Archivo subido. No se pudo calcular la huella local (el navegador no lo permite en este contexto).":localHash===meta.sha256?"Archivo subido. La huella SHA-256 del servidor coincide con la de tu archivo: el original se conservó íntegro.":"Archivo subido, pero la huella SHA-256 del servidor NO coincide con la de tu archivo. Vuelve a subirlo.");
    }catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  async function find(e:React.FormEvent){
    e.preventDefault();setError(null);setMessage("");
    const id=lookup.trim().toLowerCase();
    if(!MATERIAL_ID.test(id))return setProblem("El identificador tiene 32 caracteres hexadecimales (0-9, a-f).");
    setProblem("");setBusy(true);
    try{const meta=await getUploadedMaterial(id);remember(meta);setSelected(meta.id);setLookup("");}
    catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  return <>
    <OfflineNotice what="Trabajar con archivos y adaptaciones"/>
    <div className="grid-2 top">
      <Panel title="Subir un archivo" description="PDF o TXT, hasta 25 MB. El servidor conserva el original.">
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
    <Panel title="Archivos de este navegador" description="La API no permite listar los materiales del servidor, así que esta lista recuerda los que subiste o consultaste desde este navegador con este perfil.">
      {!items.length?<EmptyState title="Todavía no hay archivos en la lista">Sube un archivo o consulta uno por identificador.</EmptyState>:
      <ul className="picklist">{items.map(i=><li key={i.id}><button className={`pick ${i.id===selected?"active":""}`} aria-pressed={i.id===selected} onClick={()=>setSelected(i.id)}><strong>{i.filename}</strong><span className="hint">{formatBytes(i.size)} · {dateLabel(i.created_at)}</span></button></li>)}</ul>}
    </Panel>
    {current&&<Detail key={`${profile.user}:${current.id}`} material={current} onUpdated={remember} onRemove={()=>{setItems(removeUpload(profile.user,current.id));setSelected(null);}}/>}
    <Panel title="Todavía no disponible" description="Estas capacidades aparecen en el diseño del proyecto, pero su código aún no está implementado, por eso no tienen botón.">
      <ul className="plain"><li>Traducción y adaptación lingüística (incluido quechua)</li><li>Generación de audio y narración</li><li>Esquemas y organizadores visuales</li><li>Salidas accesibles adicionales</li><li>Descripción de imágenes y transcripción de audio o video</li><li>Listado de materiales en el servidor y descarga del original</li></ul>
    </Panel>
  </>;
}
export default function Materiales(){
  return <><PageHeader title="Archivos y adaptación" description="Sube PDF o TXT, extrae su texto y genera resúmenes, lectura fácil o preguntas de comprensión."/><Gate feature="materials.upload"><Inner/></Gate></>;
}
