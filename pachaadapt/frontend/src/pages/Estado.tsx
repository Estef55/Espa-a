import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {getHealth} from "../services/auth.service";
import {ErrorNotice,Loading,PageHeader,Panel} from "../components/ui";

type Row={name:string;state:"ok"|"config"|"no";detail:string};
const LABEL={ok:"Disponible",config:"Depende de la configuración",no:"No implementada"};

export default function Estado(){
  const {profile,ai,refreshAi}=useApp();
  const health=useAsync(getHealth,[]);
  const teacher=profile.role==="teacher";
  const rows:Row[]=[
    {name:"Actividades, entregas y revisión",state:"ok",detail:"Endpoints /assignments y /submissions."},
    {name:"Catálogo de materiales (enlaces)",state:"ok",detail:"Endpoint /material-library."},
    {name:"Carga de PDF/TXT, texto organizado y adaptaciones guardadas",state:"ok",detail:"Solo docente. Resumen, lectura fácil, esquema, preguntas y notas de imágenes con reglas locales (sin IA); cada una se guarda enlazada a su original y requiere revisión docente."},
    {name:"OCR de PDF escaneados y audio de las adaptaciones",state:"config",detail:"Dependen de lo instalado en el servidor (Tesseract/Poppler y un motor de voz como espeak-ng). «Qué puede hacer este servidor», en Archivos y adaptación, muestra qué hay realmente."},
    {name:"Consulta sin conexión de materiales",state:"ok",detail:"Los materiales del catálogo y los que el docente guarda con «Guardar para usar sin conexión» se consultan sin conexión. Generar adaptaciones siempre requiere conexión con el servidor."},
    {name:"Documentos editables con versiones",state:"ok",detail:"Solo docente."},
    {name:"Preferencias del docente",state:"ok",detail:"Solo docente."},
    {name:"Sincronización offline",state:"ok",detail:"Cola local, envío por lotes, conflictos de versión."},
    {name:"Asistente de IA",state:teacher&&ai.data?(ai.data.ai_provider_configured?"ok":"config"):"config",detail:teacher?(ai.data?(ai.data.ai_provider_configured?"Proveedor configurado.":"Sin proveedor de IA configurado en el servidor."):"Consultando…"):"El estado solo se consulta con el perfil Docente."},
    {name:"Importar documento desde procesador",state:teacher&&ai.data?(ai.data.document_processor_connected?"ok":"config"):"config",detail:teacher?(ai.data?(ai.data.document_processor_connected?"Procesador conectado.":"El procesador documental no está conectado."):"Consultando…"):"El estado solo se consulta con el perfil Docente."},
    {name:"Informes de resultados",state:teacher&&ai.data?(ai.data.learning_data_source_connected?"ok":"config"):"config",detail:teacher?(ai.data?(ai.data.learning_data_source_connected?"Fuente de resultados conectada.":"Sin fuente de resultados: no se pueden generar informes nuevos."):"Consultando…"):"El estado solo se consulta con el perfil Docente."},
    {name:"Autenticación real, usuarios, aulas e instituciones",state:"no",detail:"La identidad es de demostración por cabeceras."},
    {name:"Traducción, quechua, transcripción y descripción visual de imágenes",state:"no",detail:"No implementados. Tampoco hay IA ni traducción que funcione sin Internet. Braille de grado 1 existe en el servidor (/adaptations) pero sin interfaz todavía."},
    {name:"Exportación de entregas desde el servidor, notas y comentarios",state:"no",detail:"No existen endpoints; el CSV se genera en el navegador."},
  ];
  return <>
    <PageHeader title="Estado de funciones" description="Qué está disponible, qué depende de la configuración del servidor y qué aún no existe." actions={<button className="btn" onClick={()=>{health.reload();refreshAi();}}>Volver a comprobar</button>}/>
    <Panel title="Servidor">
      {health.loading&&!health.data?<Loading label="Comprobando el servidor…"/>:health.error?<ErrorNotice error={health.error} onRetry={health.reload}/>:health.data&&
      <p><span className="dot ok"/>Servidor activo · base de datos: {health.data.database} ({health.data.engine})</p>}
    </Panel>
    <Panel title="Funciones"><div className="table-wrap"><table className="data"><caption className="sr-only">Estado de las funciones</caption><thead><tr><th scope="col">Función</th><th scope="col">Estado</th><th scope="col">Detalle</th></tr></thead>
      <tbody>{rows.map(r=><tr key={r.name}><th scope="row">{r.name}</th><td><span className={`pill st-${r.state}`}>{LABEL[r.state]}</span></td><td>{r.detail}</td></tr>)}</tbody></table></div></Panel>
  </>;
}
