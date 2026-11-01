import {useEffect,useRef,type ReactNode} from "react";
import {statusLabel} from "../lib/format";
import {can,denialMessage,type Feature} from "../lib/permissions";
import {useApp} from "../context";
import type {ApiError} from "../services/http";

export function PageHeader({title,description,actions}:{title:string;description?:string;actions?:ReactNode}){
  const ref=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{ref.current?.focus({preventScroll:true});},[]); // al navegar, el foco pasa al título (lectores de pantalla)
  return <div className="page-head"><div><h1 ref={ref} tabIndex={-1}>{title}</h1>{description&&<p className="lead">{description}</p>}</div>{actions&&<div className="page-actions">{actions}</div>}</div>;
}
export function Panel({title,description,actions,children,id}:{title?:string;description?:string;actions?:ReactNode;children:ReactNode;id?:string}){
  return <section className="panel" aria-labelledby={title&&id?`${id}-t`:undefined} id={id}>
    {(title||actions)&&<div className="panel-head"><div>{title&&<h2 id={id?`${id}-t`:undefined}>{title}</h2>}{description&&<p className="hint">{description}</p>}</div>{actions&&<div className="row">{actions}</div>}</div>}
    {children}</section>;
}
export type NoticeKind="error"|"success"|"info"|"warn";
export function Notice({kind="info",children,action}:{kind?:NoticeKind;children:ReactNode;action?:ReactNode}){
  return <div className={`notice ${kind}`} role={kind==="error"?"alert":"status"}><div>{children}</div>{action&&<div className="notice-action">{action}</div>}</div>;
}
export function Loading({label="Cargando…"}:{label?:string}){return <p className="loading" role="status"><span className="spinner" aria-hidden="true"/>{label}</p>;}
export function EmptyState({title,children,action}:{title:string;children?:ReactNode;action?:ReactNode}){
  return <div className="empty"><strong>{title}</strong>{children&&<p>{children}</p>}{action}</div>;
}
export function StatusPill({status}:{status:string}){return <span className={`pill ${status}`}>{statusLabel(status)}</span>;}
export function Field({label,hint,children}:{label:string;hint?:string;children:ReactNode}){
  return <label className="field"><span className="field-label">{label}</span>{children}{hint&&<span className="hint">{hint}</span>}</label>;
}
/** Muestra el error del servicio con una pista según su tipo (permisos, función no disponible, conflicto…). */
export function ErrorNotice({error,onRetry,retryLabel="Reintentar"}:{error:Error;onRetry?:()=>void;retryLabel?:string}){
  const kind=(error as ApiError).kind;
  const title=kind==="forbidden"?"Permisos insuficientes":kind==="unavailable"||kind==="not_implemented"?"Función no disponible":kind==="network"?"Sin conexión con el servidor":kind==="conflict"?"Conflicto de versión":"No se pudo completar la acción";
  return <Notice kind={kind==="unavailable"||kind==="not_implemented"?"warn":"error"} action={onRetry&&<button className="btn btn-quiet" onClick={onRetry}>{retryLabel}</button>}><strong>{title}.</strong> {error.message}</Notice>;
}
/** Bloquea una pantalla cuando el perfil actual no tiene permiso (el servidor lo vuelve a exigir). */
export function Gate({feature,children}:{feature:Feature;children:ReactNode}){
  const {profile}=useApp();
  if(!can(profile.role,feature))return <Notice kind="warn"><strong>Permisos insuficientes.</strong> {denialMessage(profile.role,feature)} <a href="#/perfil">Ir a Perfil</a></Notice>;
  return <>{children}</>;
}
export function OfflineNotice({what}:{what:string}){
  const {online}=useApp();
  return online?null:<Notice kind="warn"><strong>Sin conexión.</strong> {what} necesita conexión con el servidor; vuelve a intentarlo cuando se restablezca.</Notice>;
}
export function CachedNotice({savedAt}:{savedAt?:string}){
  return <Notice kind="info">Mostrando la copia guardada en este dispositivo{savedAt?` (${new Date(savedAt).toLocaleString("es-PE",{dateStyle:"medium",timeStyle:"short"})})`:""}. Puede estar desactualizada.</Notice>;
}
/** Estado de una integración del backend que puede no estar configurada. */
export function NotConnected({children}:{children:ReactNode}){return <Notice kind="warn"><strong>Función pendiente en el servidor.</strong> {children}</Notice>;}
