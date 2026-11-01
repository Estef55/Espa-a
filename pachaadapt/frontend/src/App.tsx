import {useEffect,useState,type ReactNode} from "react";
import {AppProvider,useApp} from "./context";
import {ROUTES,hrefFor,parseHash,routeLabel,type RouteId} from "./lib/router";
import {ROLE_LABEL} from "./services/auth.service";
import {Notice} from "./components/ui";
import Inicio from "./pages/Inicio";
import Actividades from "./pages/Actividades";
import Entregas from "./pages/Entregas";
import Catalogo from "./pages/Catalogo";
import Materiales from "./pages/Materiales";
import Documentos from "./pages/Documentos";
import Asistente from "./pages/Asistente";
import Preferencias from "./pages/Preferencias";
import Informes from "./pages/Informes";
import Sincronizacion from "./pages/Sincronizacion";
import Estado from "./pages/Estado";
import Perfil from "./pages/Perfil";
import "./styles.css";

const PAGES:Record<RouteId,()=>ReactNode>={
  inicio:()=><Inicio/>,actividades:()=><Actividades/>,entregas:()=><Entregas/>,catalogo:()=><Catalogo/>,materiales:()=><Materiales/>,
  documentos:()=><Documentos/>,asistente:()=><Asistente/>,preferencias:()=><Preferencias/>,informes:()=><Informes/>,
  sincronizacion:()=><Sincronizacion/>,estado:()=><Estado/>,perfil:()=><Perfil/>,
};

function Shell(){
  const {profile,online,sync,conflicts,backend,epoch,checkBackend}=useApp();
  const [route,setRoute]=useState<RouteId>(parseHash(location.hash));
  const [menu,setMenu]=useState(false);
  useEffect(()=>{
    const onHash=()=>{setRoute(parseHash(location.hash));setMenu(false);};
    const onKey=(e:KeyboardEvent)=>{if(e.key==="Escape")setMenu(false);};
    addEventListener("hashchange",onHash);addEventListener("keydown",onKey);
    return ()=>{removeEventListener("hashchange",onHash);removeEventListener("keydown",onKey);};
  },[]);
  useEffect(()=>{document.title=`${routeLabel(route,profile.role)} · PACHAADAPT`;},[route,profile.role]);
  const groups=[...new Set(ROUTES.map(r=>r.group))];
  const down=online&&backend==="down";
  const connection=!online?"Sin conexión":down?"Backend sin respuesta":sync.syncing?"Sincronizando":sync.pending?`${sync.pending} pendiente(s)`:"Con conexión";
  return <div className="shell">
    <a className="skip-link" href="#contenido" onClick={e=>{e.preventDefault();document.getElementById("contenido")?.focus();}}>Saltar al contenido</a>
    <header className="topbar">
      <button className="menu-btn" aria-expanded={menu} aria-controls="nav" onClick={()=>setMenu(m=>!m)}>Menú</button>
      <a className="brand" href={hrefFor("inicio")}><span className="brand-mark" aria-hidden="true">P</span><span><strong>PACHAADAPT</strong><span className="brand-sub">Aprendizaje accesible</span></span></a>
      <div className="top-status">
        <a className={`chip ${!online||down?"off":sync.pending?"warn":"ok"}`} href={hrefFor("sincronizacion")} aria-label={`Conexión: ${connection}. Abrir sincronización`}><span className="dot"/>{connection}</a>
        <a className="chip demo" href={hrefFor("perfil")} title="Identidad de demostración, no es un inicio de sesión">Demostración · {ROLE_LABEL[profile.role]}</a>
      </div>
    </header>
    <nav id="nav" className={`sidebar ${menu?"open":""}`} aria-label="Principal">
      {groups.map(g=><div className="nav-group" key={g}><p className="nav-title">{g}</p><ul>{ROUTES.filter(r=>r.group===g).map(r=>
        <li key={r.id}><a className="nav-link" href={hrefFor(r.id)} aria-current={r.id===route?"page":undefined}>{routeLabel(r.id,profile.role)}{r.only&&!r.only.includes(profile.role)&&<span className="nav-tag">Docente</span>}</a></li>)}</ul></div>)}
    </nav>
    <main id="contenido" tabIndex={-1} className="content">
      {down&&<Notice kind="error" action={<button className="btn btn-quiet" onClick={checkBackend}>Comprobar ahora</button>}><strong>No hay conexión con el backend.</strong> El navegador tiene red, pero el servidor de PACHAADAPT no responde. Inicia el backend en otra terminal (<code>python scripts/start_server.py</code>) y déjala abierta; esta pantalla se actualizará sola cuando responda.</Notice>}
      {!online&&<Notice kind="warn"><strong>Sin conexión.</strong> Puedes leer lo que ya se descargó y escribir respuestas; se enviarán al volver la red.</Notice>}
      {conflicts.length>0&&route!=="sincronizacion"&&<Notice kind="warn" action={<a className="btn btn-quiet" href={hrefFor("sincronizacion")}>Resolver</a>}><strong>{conflicts.length} conflicto(s) de sincronización pendientes.</strong></Notice>}
      {/* Las pantallas se reinician al cambiar de perfil (sus datos son del perfil anterior), salvo Perfil, que conserva su mensaje de confirmación. */}
      <div key={route==="perfil"?"perfil":`${route}:${profile.role}:${profile.user}:${epoch}`}>{PAGES[route]()}</div>
    </main>
    <footer className="foot">Los perfiles de demostración usan cabeceras locales. Antes de publicar en Internet deben activarse autenticación real y HTTPS.</footer>
  </div>;
}
export default function App(){return <AppProvider><Shell/></AppProvider>;}
