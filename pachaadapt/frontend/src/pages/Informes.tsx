import {useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {createReport,getReport,getReportMarkdown,listReports} from "../services/reports.service";
import {downloadText} from "../lib/csv";
import {dateLabel,statusLabel} from "../lib/format";
import type {Report,ReportCriteria} from "../lib/types";
import {EmptyState,ErrorNotice,Field,Gate,Loading,Notice,NotConnected,OfflineNotice,PageHeader,Panel,StatusPill} from "../components/ui";

const show=(v:unknown)=>v===null||v===undefined?"—":typeof v==="object"?JSON.stringify(v):String(v);
const asError=(e:unknown)=>e instanceof Error?e:new Error(String(e));

function ReportView({id}:{id:string}){
  const r=useAsync(()=>getReport(id),[id]);
  const [md,setMd]=useState<string|null>(null);const [error,setError]=useState<Error|null>(null);
  async function loadMd(){setError(null);try{setMd(await getReportMarkdown(id));}catch(e){setError(asError(e));}}
  if(r.loading&&!r.data)return <Loading label="Cargando informe…"/>;
  if(r.error)return <ErrorNotice error={r.error} onRetry={r.reload}/>;
  const rep:Report|undefined=r.data;if(!rep)return null;
  return <div className="stack">
    <Panel title={`Informe del ${dateLabel(rep.created_at)}`} actions={<><button className="btn" onClick={()=>void loadMd()}>Ver en Markdown</button>{md&&<button className="btn" onClick={()=>downloadText(`informe_${rep.id.slice(0,8)}.md`,md,"text/markdown;charset=utf-8")}>Descargar .md</button>}</>}>
      <p className="meta"><span>Estado: <StatusPill status={rep.status}/></span>{rep.data_summary&&<span>Registros usados: {rep.data_summary.records_used} de {rep.data_summary.records_received} ({rep.data_summary.records_invalid} inválidos) · fuente {rep.data_summary.source}</span>}</p>
      <dl className="kv">{Object.entries(rep.criteria).map(([k,v])=><div className="kv-row" key={k}><dt>{k}</dt><dd>{show(v)}</dd></div>)}</dl>
      {rep.status!=="ok"&&<Notice kind="warn"><strong>Datos insuficientes.</strong><ul>{(rep.missing??[]).map(m=><li key={m}>{m}</li>)}</ul></Notice>}
      {rep.metrics&&<div className="grid-2">
        <div><h3>Valores medidos</h3><dl className="kv">{Object.entries(rep.metrics.measured??{}).map(([k,v])=><div className="kv-row" key={k}><dt>{k}</dt><dd>{show(v)}</dd></div>)}</dl></div>
        <div><h3>Valores calculados</h3><dl className="kv">{Object.entries(rep.metrics.calculated??{}).filter(([k])=>k!=="trend").map(([k,v])=><div className="kv-row" key={k}><dt>{k}</dt><dd>{show(v)}</dd></div>)}</dl></div></div>}
      {!!rep.observations?.length&&<><h3>Observaciones</h3><ul className="plain">{rep.observations.map(o=><li key={o.id}><strong>{o.id}</strong> ({o.kind}): {o.text}</li>)}</ul></>}
      {!!rep.recommendations?.length&&<><h3>Recomendaciones</h3><ul className="plain">{rep.recommendations.map(o=><li key={o.id}><strong>{o.id}</strong> (según {o.based_on.join(", ")}): {o.text}</li>)}</ul></>}
      {rep.ai_interpretation&&<><h3>Interpretación generada por IA</h3>{rep.ai_interpretation.status==="ok"?<p className="prewrap">{rep.ai_interpretation.text}</p>:<Notice kind="warn">No disponible: {rep.ai_interpretation.reason}</Notice>}<p className="hint">Es una interpretación de un modelo, no un dato.</p></>}
      {!!rep.limitations?.length&&<><h3>Limitaciones</h3><ul className="plain">{rep.limitations.map(l=><li key={l}>{l}</li>)}</ul></>}
      {error&&<ErrorNotice error={error}/>}{md&&<pre className="output">{md}</pre>}
    </Panel></div>;
}

function Inner(){
  const {ai,online}=useApp();
  const list=useAsync(listReports,[]);
  const [selected,setSelected]=useState<string|null>(null);
  const [form,setForm]=useState({threshold:"",topic:"",group:"",from:"",to:"",ai:false});
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [problem,setProblem]=useState("");
  const connected=!!ai.data?.learning_data_source_connected;
  async function generate(e:React.FormEvent){
    e.preventDefault();setError(null);
    const t=form.threshold.trim()===""?undefined:Number(form.threshold);
    if(t!==undefined&&!(t>0&&t<=100))return setProblem("El umbral de aprobación debe ser un número mayor que 0 y hasta 100.");
    if(form.from&&form.to&&form.from>form.to)return setProblem("La fecha inicial no puede ser posterior a la final.");
    setProblem("");setBusy(true);
    try{
      const criteria:ReportCriteria={pass_threshold_pct:t,topic:form.topic.trim()||undefined,group:form.group.trim()||undefined,date_from:form.from||undefined,date_to:form.to||undefined,...(form.ai?{include_ai_interpretation:true}:{})};
      const rep=await createReport(criteria);setSelected(rep.id);list.reload();
    }catch(err){setError(asError(err));}finally{setBusy(false);}
  }
  return <>
    <OfflineNotice what="Los informes"/>
    <Panel title="Generar un informe" description="Analiza resultados de aprendizaje agregados; no evalúa a estudiantes individuales.">
      {!connected?<NotConnected>{ai.loading?"Comprobando el estado del servidor…":ai.error?`No se pudo consultar el estado: ${ai.error.message}`:"El servidor no tiene conectada una fuente de resultados de aprendizaje, por lo que no puede generar informes (no se inventan datos). Los informes ya generados siguen disponibles abajo."}</NotConnected>:
      <form className="form" onSubmit={e=>void generate(e)} noValidate>
        <div className="grid-2">
          <Field label="Umbral de aprobación (%)" hint="Opcional. Por defecto 55. Es un criterio configurable, no una norma oficial."><input type="number" min={1} max={100} step="any" value={form.threshold} onChange={e=>setForm({...form,threshold:e.target.value})}/></Field>
          <Field label="Tema (opcional)"><input value={form.topic} onChange={e=>setForm({...form,topic:e.target.value})} maxLength={120}/></Field>
          <Field label="Grupo (opcional)"><input value={form.group} onChange={e=>setForm({...form,group:e.target.value})} maxLength={120}/></Field>
          <div className="grid-2"><Field label="Desde"><input type="date" value={form.from} onChange={e=>setForm({...form,from:e.target.value})}/></Field><Field label="Hasta"><input type="date" value={form.to} onChange={e=>setForm({...form,to:e.target.value})}/></Field></div>
        </div>
        <label className="check"><input type="checkbox" checked={form.ai} onChange={e=>setForm({...form,ai:e.target.checked})} disabled={!ai.data?.ai_provider_configured}/> Incluir interpretación de IA {!ai.data?.ai_provider_configured&&<span className="hint">(requiere proveedor de IA configurado)</span>}</label>
        {problem&&<Notice kind="error">{problem}</Notice>}{error&&<ErrorNotice error={error}/>}
        <div><button className="btn btn-primary" disabled={busy||!online}>{busy?"Generando…":"Generar informe"}</button></div>
      </form>}
    </Panel>
    <div className="split">
      <Panel title="Informes generados">
        {list.loading&&!list.data?<Loading/>:list.error?<ErrorNotice error={list.error} onRetry={list.reload}/>:!list.data?.length?<EmptyState title="Todavía no hay informes">{connected?"Genera el primero con el formulario.":"Cuando el servidor tenga una fuente de datos conectada podrás generarlos."}</EmptyState>:
        <ul className="picklist">{list.data.map(i=><li key={i.id}><button className={`pick ${i.id===selected?"active":""}`} aria-pressed={i.id===selected} onClick={()=>setSelected(i.id)}><strong>{dateLabel(i.created_at)}</strong><span className="hint">{statusLabel(i.status)}</span></button></li>)}</ul>}
      </Panel>
      <div>{selected?<ReportView key={selected} id={selected}/>:<EmptyState title="Selecciona un informe">Elige uno de la lista para ver sus resultados.</EmptyState>}</div>
    </div>
  </>;
}
export default function Informes(){
  return <><PageHeader title="Informes" description="Informes de resultados de aprendizaje con valores medidos, calculados y generados por IA claramente separados."/><Gate feature="reports"><Inner/></Gate></>;
}
