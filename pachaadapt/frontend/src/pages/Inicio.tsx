import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {fetchAssignments,fetchMaterials,getSubmissions} from "../services/assignments.service";
import {ROLE_LABEL} from "../services/auth.service";
import {routeLabel,hrefFor,type RouteId} from "../lib/router";
import {Loading,Notice,PageHeader,Panel} from "../components/ui";

const SHORTCUTS:Record<string,{id:RouteId;text:string}[]>={
  student:[{id:"actividades",text:"Lee las actividades publicadas y envía tus respuestas."},{id:"entregas",text:"Consulta el estado de lo que ya enviaste."},{id:"catalogo",text:"Abre los materiales de estudio."},{id:"sincronizacion",text:"Revisa respuestas pendientes de envío."}],
  teacher:[{id:"actividades",text:"Crea, edita y filtra actividades."},{id:"entregas",text:"Revisa, devuelve y exporta respuestas."},{id:"materiales",text:"Sube PDF/TXT, extrae texto y genera adaptaciones."},{id:"documentos",text:"Edita documentos con historial de versiones."},{id:"asistente",text:"Consulta al asistente sobre un documento."},{id:"informes",text:"Genera informes de resultados."}],
  admin:[{id:"actividades",text:"Consulta y edita cualquier actividad."},{id:"entregas",text:"Revisa entregas de todas las actividades."},{id:"catalogo",text:"Administra el catálogo de materiales."},{id:"estado",text:"Mira qué funciones están disponibles."}],
};

export default function Inicio(){
  const {profile,sync,online,conflicts,ai}=useApp();
  const dep=[profile.user,profile.role];
  const assignments=useAsync(fetchAssignments,dep);
  const submissions=useAsync(()=>getSubmissions(),dep);
  const library=useAsync(fetchMaterials,dep);
  const staff=profile.role!=="student";
  const list=assignments.data?.data??[],subs=submissions.data??[];
  const stats:[string,string|number,string][]=[
    ["Actividades",assignments.error?"—":list.length,assignments.error?"No se pudieron cargar":`${list.filter(a=>a.status==="published").length} publicadas`],
    staff?["Entregas por revisar",submissions.error?"—":subs.filter(s=>s.status==="submitted").length,submissions.error?"No se pudieron cargar":`${subs.length} recibidas`]
      :["Mis entregas",submissions.error?"—":subs.length,submissions.error?"No se pudieron cargar":`${subs.filter(s=>s.status==="reviewed").length} revisadas`],
    ["Catálogo",library.error?"—":(library.data?.data??[]).length,"materiales"],
    ["Pendientes de envío",sync.pending,online?"se envían solos al conectar":"sin conexión"],
  ];
  return <>
    <PageHeader title={profile.role==="student"?"Hola, continúa aprendiendo":"Panel de gestión educativa"} description={`Sesión de demostración como ${ROLE_LABEL[profile.role].toLowerCase()} (${profile.user}).`}/>
    {conflicts.length>0&&<Notice kind="warn" action={<a className="btn btn-quiet" href={hrefFor("sincronizacion")}>Resolver</a>}><strong>{conflicts.length} conflicto(s) de sincronización.</strong> Una respuesta cambió en el servidor mientras estabas sin conexión.</Notice>}
    {sync.otherProfiles?<Notice kind="info">Hay {sync.otherProfiles} respuesta(s) pendiente(s) de otro perfil de demostración; se enviarán cuando vuelvas a ese perfil.</Notice>:null}
    {(assignments.loading&&!assignments.data)?<Loading label="Cargando resumen…"/>:
    <dl className="stats">{stats.map(([label,value,note])=><div className="stat" key={label}><dt>{label}</dt><dd>{value}</dd><span className="hint">{note}</span></div>)}</dl>}
    {assignments.data?.fromCache&&<Notice kind="info">Resumen calculado con la copia guardada en este dispositivo.</Notice>}
    {assignments.error&&<Notice kind="error">No se pudieron cargar las actividades: {assignments.error.message}</Notice>}
    <div className="grid-2">
      <Panel title="Accesos">
        <ul className="linklist">{SHORTCUTS[profile.role].map(s=><li key={s.id}><a href={hrefFor(s.id)}>{routeLabel(s.id,profile.role)}</a><span className="hint">{s.text}</span></li>)}</ul>
      </Panel>
      <Panel title="Estado de integraciones" description="Funciones que dependen de la configuración del servidor.">
        {profile.role!=="teacher"?<p className="hint">El detalle de integraciones de IA, procesador documental e informes solo se consulta con el perfil Docente. Mira <a href="#/estado">Estado de funciones</a>.</p>
        :ai.loading&&!ai.data?<Loading/>:ai.error?<Notice kind="error">No se pudo consultar el estado: {ai.error.message}</Notice>:ai.data&&
        <ul className="statuslist">
          <li><span className={`dot ${ai.data.ai_provider_configured?"ok":"off"}`}/>Proveedor de IA: {ai.data.ai_provider_configured?"configurado":"sin configurar"}</li>
          <li><span className={`dot ${ai.data.document_processor_connected?"ok":"off"}`}/>Procesador documental (importar): {ai.data.document_processor_connected?"conectado":"sin conectar"}</li>
          <li><span className={`dot ${ai.data.learning_data_source_connected?"ok":"off"}`}/>Fuente de resultados (informes): {ai.data.learning_data_source_connected?"conectada":"sin conectar"}</li>
        </ul>}
      </Panel>
    </div>
  </>;
}
