import {useEffect,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {getAdaptationParams,getPreferences,updatePreferences} from "../services/preferences.service";
import {dateLabel} from "../lib/format";
import type {PreferenceKey,Preferences} from "../lib/types";
import {ErrorNotice,Field,Gate,Loading,Notice,OfflineNotice,PageHeader,Panel} from "../components/ui";

const FIELDS:{key:PreferenceKey;label:string;hint?:string;values:Record<string,string>}[]=[
  {key:"education_level",label:"Nivel educativo",hint:"Opcional: el nivel piloto aún no está validado.",values:{inicial:"Inicial",primaria:"Primaria",secundaria:"Secundaria"}},
  {key:"complexity",label:"Complejidad",values:{basico:"Básica",intermedio:"Intermedia",avanzado:"Avanzada"}},
  {key:"length",label:"Extensión de las respuestas",values:{corta:"Corta",media:"Media",larga:"Larga"}},
  {key:"tone",label:"Tono",values:{formal:"Formal",cercano:"Cercano",neutro:"Neutro"}},
  {key:"format",label:"Formato de presentación",values:{texto:"Texto",esquema:"Esquema",lista:"Lista"}},
  {key:"language",label:"Idioma de respuesta",hint:"Las respuestas en quechua no están validadas con la comunidad.",values:{es:"Español",qu:"Quechua (Runasimi)"}},
];
const toForm=(p:Preferences)=>Object.fromEntries(FIELDS.map(f=>[f.key,p[f.key]??""])) as Record<PreferenceKey,string>;

function Inner(){
  const {profile,online}=useApp();
  const prefs=useAsync(getPreferences,[profile.user]);
  const [form,setForm]=useState<Record<PreferenceKey,string>|null>(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState<Error|null>(null);const [message,setMessage]=useState("");
  const [params,setParams]=useState<Record<string,string>|null>(null);const [paramsError,setParamsError]=useState<Error|null>(null);
  useEffect(()=>{if(prefs.data)setForm(toForm(prefs.data.preferences));},[prefs.data]);
  if(prefs.loading&&!prefs.data)return <Loading label="Cargando preferencias…"/>;
  if(prefs.error)return <ErrorNotice error={prefs.error} onRetry={prefs.reload}/>;
  if(!prefs.data||!form)return null;
  const saved=prefs.data.preferences;
  const changes:Partial<Preferences>={};
  for(const f of FIELDS){const now=form[f.key]===""?null:form[f.key];if(now!==saved[f.key])changes[f.key]=now;}
  const dirty=Object.keys(changes).length>0;

  async function save(e:React.FormEvent){
    e.preventDefault();setBusy(true);setError(null);setMessage("");
    try{const r=await updatePreferences(changes);prefs.setData(r);setMessage("Preferencias guardadas.");setParams(null);}
    catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setBusy(false);}
  }
  async function loadParams(){
    setParamsError(null);
    try{setParams((await getAdaptationParams()).proposed_params);}catch(err){setParamsError(err instanceof Error?err:new Error(String(err)));}
  }
  return <>
    <OfflineNotice what="Guardar preferencias"/>
    {prefs.data.is_default&&<Notice kind="info">Aún no has guardado preferencias: se muestran los valores por defecto.</Notice>}
    <Panel title="Mis preferencias" description={prefs.data.updated_at?`Última modificación: ${dateLabel(prefs.data.updated_at)}`:undefined}>
      <form className="form" onSubmit={e=>void save(e)}>
        <div className="grid-2">{FIELDS.map(f=><Field key={f.key} label={f.label} hint={f.hint}>
          <select value={form[f.key]} onChange={e=>setForm({...form,[f.key]:e.target.value})}>
            {f.key==="education_level"&&<option value="">Sin especificar</option>}
            {(prefs.data!.allowed_values[f.key]??Object.keys(f.values)).map(v=><option key={v} value={v}>{f.values[v]??v}</option>)}
          </select></Field>)}</div>
        {error&&<ErrorNotice error={error}/>}{message&&<Notice kind="success">{message}</Notice>}
        <div className="row"><button className="btn btn-primary" disabled={busy||!dirty||!online}>{busy?"Guardando…":"Guardar preferencias"}</button><button type="button" className="btn btn-quiet" disabled={!dirty} onClick={()=>setForm(toForm(saved))}>Descartar cambios</button></div>
      </form>
      <p className="hint">El asistente de IA aplica estas preferencias en sus respuestas.</p>
    </Panel>
    <Panel title="Parámetros propuestos para adaptaciones" description="El servidor traduce tus preferencias a parámetros de adaptación. Es solo una propuesta: todavía no se aplican automáticamente en «Archivos y adaptación».">
      <div><button className="btn" onClick={()=>void loadParams()} disabled={!online}>Ver parámetros propuestos</button></div>
      {paramsError&&<ErrorNotice error={paramsError}/>}
      {params&&(Object.keys(params).length?<dl className="kv">{Object.entries(params).map(([k,v])=><div key={k} className="kv-row"><dt>{FIELDS.find(f=>f.key===k)?.label??k}</dt><dd>{FIELDS.find(f=>f.key===k)?.values[v]??v}</dd></div>)}</dl>:<p className="hint">No hay parámetros: ninguna preferencia está especificada.</p>)}
    </Panel>
  </>;
}
export default function Preferencias(){
  return <><PageHeader title="Preferencias" description="Define cómo quieres que el asistente responda. Se guardan en el servidor para tu usuario."/><Gate feature="preferences"><Inner/></Gate></>;
}
