// Navegación por hash (#/ruta): no requiere dependencias y funciona con la PWA sin conexión.
import type {Role} from "./types";
export type RouteId="inicio"|"actividades"|"entregas"|"catalogo"|"materiales"|"documentos"|"asistente"|"preferencias"|"informes"|"sincronizacion"|"estado"|"perfil";
export type RouteDef={id:RouteId;label:string;group:string;only?:Role[];needsConnection?:boolean};
export const ROUTES:RouteDef[]=[
  {id:"inicio",label:"Inicio",group:"General"},
  {id:"actividades",label:"Actividades",group:"Trabajo en aula"},
  {id:"entregas",label:"Entregas",group:"Trabajo en aula"},
  {id:"catalogo",label:"Catálogo de materiales",group:"Materiales"},
  {id:"materiales",label:"Archivos y adaptación",group:"Materiales",only:["teacher"],needsConnection:true},
  {id:"documentos",label:"Documentos editables",group:"Asistente docente",only:["teacher"],needsConnection:true},
  {id:"asistente",label:"Asistente de IA",group:"Asistente docente",only:["teacher"],needsConnection:true},
  {id:"preferencias",label:"Preferencias",group:"Asistente docente",only:["teacher"],needsConnection:true},
  {id:"informes",label:"Informes",group:"Asistente docente",only:["teacher"],needsConnection:true},
  {id:"sincronizacion",label:"Conexión y sincronización",group:"Sistema"},
  {id:"estado",label:"Estado de funciones",group:"Sistema"},
  {id:"perfil",label:"Perfil de demostración",group:"Sistema"},
];
export const routeLabel=(id:RouteId,role:Role)=>id==="entregas"?(role==="student"?"Mis entregas":"Entregas recibidas"):ROUTES.find(r=>r.id===id)?.label??id;
export function parseHash(hash:string):RouteId{
  const id=hash.replace(/^#\/?/,"").split(/[/?]/)[0] as RouteId;
  return ROUTES.some(r=>r.id===id)?id:"inicio";
}
export const hrefFor=(id:RouteId)=>`#/${id}`;
