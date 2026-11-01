import {useState} from "react";
import {useApp} from "../context";
import {DEMO_USERS,ROLE_LABEL,isValidUserId} from "../services/auth.service";
import {getServerSyncStatus} from "../services/sync.service";
import {can,type Feature} from "../lib/permissions";
import type {Role,SyncServerStatus} from "../lib/types";
import {ErrorNotice,Field,Notice,PageHeader,Panel} from "../components/ui";

const FEATURES:[Feature,string][]=[["assignments.write","Crear y editar actividades"],["submissions.send","Enviar respuestas"],["submissions.review","Revisar y devolver entregas"],["library.write","Registrar materiales en el catálogo"],["materials.upload","Subir y adaptar archivos"],["documents","Documentos editables"],["chat","Asistente de IA"],["preferences","Preferencias"],["reports","Informes"]];

export default function Perfil(){
  const {profile,setProfile}=useApp();
  const [role,setRole]=useState<Role>(profile.role);const [user,setUser]=useState(profile.user);
  const [problem,setProblem]=useState("");const [message,setMessage]=useState("");
  const [probe,setProbe]=useState<SyncServerStatus|null>(null);const [probeError,setProbeError]=useState<Error|null>(null);
  function apply(e:React.FormEvent){
    e.preventDefault();setMessage("");setProbe(null);
    if(!isValidUserId(user))return setProblem("El usuario admite letras, números y . _ @ - (hasta 64 caracteres).");
    setProblem("");setProfile({role,user});setMessage(`Perfil aplicado: ${ROLE_LABEL[role]} (${user}).`);
  }
  async function test(){setProbe(null);setProbeError(null);try{setProbe(await getServerSyncStatus());}catch(e){setProbeError(e instanceof Error?e:new Error(String(e)));}}
  return <>
    <PageHeader title="Perfil de demostración" description="PACHAADAPT todavía no tiene inicio de sesión."/>
    <Notice kind="warn"><strong>Identidad de demostración.</strong> El perfil se envía al servidor en las cabeceras <code>X-User-Id</code> y <code>X-Role</code>, y cualquiera puede cambiarlo. El servidor solo las acepta con <code>PACHAADAPT_I3_DEV_AUTH=1</code>. No usar en Internet sin autenticación real.</Notice>
    <Panel title="Perfil activo" description={`Ahora: ${ROLE_LABEL[profile.role]} (${profile.user})`}>
      <form className="form" onSubmit={apply} noValidate>
        <div className="grid-2">
          <Field label="Rol"><select value={role} onChange={e=>{const r=e.target.value as Role;setRole(r);setUser(DEMO_USERS[r]);}}><option value="student">Estudiante</option><option value="teacher">Docente</option><option value="admin">Administrador</option></select></Field>
          <Field label="Usuario" hint="Dos usuarios distintos tienen datos separados (documentos, preferencias, entregas)."><input value={user} onChange={e=>setUser(e.target.value)} maxLength={64} className="mono" spellCheck={false}/></Field>
        </div>
        {problem&&<Notice kind="error">{problem}</Notice>}{message&&<Notice kind="success">{message}</Notice>}
        <div className="row"><button className="btn btn-primary">Aplicar perfil</button><button type="button" className="btn btn-quiet" onClick={()=>void test()}>Probar con el servidor</button></div>
        {probe&&<Notice kind="success">El servidor reconoce al usuario <strong>{probe.actor_id}</strong>.</Notice>}{probeError&&<ErrorNotice error={probeError}/>}
      </form>
    </Panel>
    <Panel title="Qué puede hacer este perfil"><ul className="plain">{FEATURES.map(([f,l])=><li key={f}>{can(profile.role,f)?"✔":"✖"} {l}</li>)}</ul></Panel>
  </>;
}
