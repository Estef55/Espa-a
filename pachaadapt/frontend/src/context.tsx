import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from "react";
import {setActor} from "./services/http";
import {loadProfile,saveProfile,type Profile} from "./services/auth.service";
import {getAiStatus} from "./services/ai.service";
import {getHealth} from "./services/auth.service";
import type {ApiError} from "./services/http";
import {can} from "./lib/permissions";
import {conflictFromEvent,type SyncConflict} from "./lib/conflicts";
import {watchSyncStatus,type SyncState} from "./offline/sync-status";
import {synchronize} from "./offline/sync-queue"; // importar el módulo también activa la sincronización automática al volver la conexión
import type {AiStatus} from "./lib/types";

export type SyncEvent={id:number;at:string;text:string};
type AiStatusState={loading:boolean;data?:AiStatus;error?:Error};
type AppState={
  profile:Profile;setProfile:(p:Profile)=>void;online:boolean;sync:SyncState;
  conflicts:SyncConflict[];removeConflict:(operationId:string)=>void;events:SyncEvent[];
  ai:AiStatusState;refreshAi:()=>void;
  /** "down": el navegador tiene red pero el backend no responde. `epoch` cambia cuando el backend vuelve, para recargar la pantalla. */
  backend:"unknown"|"up"|"down";epoch:number;checkBackend:()=>void;
};
const Ctx=createContext<AppState|null>(null);
export const useApp=()=>{const v=useContext(Ctx);if(!v)throw new Error("useApp debe usarse dentro de AppProvider");return v;};

// La identidad se fija antes del primer render para que ninguna petición salga con otra distinta.
const initial=loadProfile();setActor(initial.user,initial.role);

export function AppProvider({children}:{children:ReactNode}){
  const [profile,setProfileState]=useState<Profile>(initial);
  const [online,setOnline]=useState(navigator.onLine);
  const [sync,setSync]=useState<SyncState>({online:navigator.onLine,pending:0,syncing:false});
  const [conflicts,setConflicts]=useState<SyncConflict[]>([]);
  const [events,setEvents]=useState<SyncEvent[]>([]);
  const [ai,setAi]=useState<AiStatusState>({loading:false});
  const [backend,setBackend]=useState<"unknown"|"up"|"down">("unknown");const [epoch,setEpoch]=useState(0);
  const lastBackend=useRef<"unknown"|"up"|"down">("unknown");
  const eventId=useRef(0);

  const setProfile=useCallback((p:Profile)=>{
    setActor(p.user,p.role);saveProfile(p);setConflicts([]);setProfileState(p);
    window.dispatchEvent(new Event("pacha-sync-change"));
  },[]);
  const removeConflict=useCallback((id:string)=>setConflicts(list=>list.filter(c=>c.operation.operation_id!==id)),[]);
  const pushEvent=useCallback((text:string)=>setEvents(list=>[{id:++eventId.current,at:new Date().toISOString(),text},...list].slice(0,15)),[]);

  useEffect(()=>{
    const stop=watchSyncStatus(setSync);
    const on=()=>setOnline(true),off=()=>setOnline(false);
    const onConflict=(e:Event)=>{
      const conflict=conflictFromEvent((e as CustomEvent).detail);if(!conflict)return;
      setConflicts(list=>list.some(c=>c.operation.operation_id===conflict.operation.operation_id)?list:[...list,conflict]);
    };
    const onRejected=(e:Event)=>{
      const d=(e as CustomEvent).detail as {status?:number;reason?:string}|undefined;
      pushEvent(`El servidor rechazó una respuesta pendiente (${d?.reason??`código ${d?.status??"desconocido"}`}). Se descartó de la cola.`);
    };
    window.addEventListener("online",on);window.addEventListener("offline",off);
    window.addEventListener("pacha-sync-conflict",onConflict);window.addEventListener("pacha-sync-rejected",onRejected);
    return ()=>{stop();window.removeEventListener("online",on);window.removeEventListener("offline",off);
      window.removeEventListener("pacha-sync-conflict",onConflict);window.removeEventListener("pacha-sync-rejected",onRejected);};
  },[pushEvent]);

  // Sincronización automática: al abrir la app y al cambiar de perfil (solo envía las operaciones del perfil activo).
  useEffect(()=>{if(navigator.onLine&&profile.role==="student")void synchronize();},[profile.user,profile.role]);

  const refreshAi=useCallback(()=>{
    if(!can(profile.role,"chat")){setAi({loading:false});return;}
    setAi(s=>({data:s.data,loading:true}));
    getAiStatus().then(data=>setAi({loading:false,data})).catch((error:Error)=>setAi({loading:false,error}));
  },[profile.role,profile.user]);
  useEffect(()=>{refreshAi();},[refreshAi]);

  const checkBackend=useCallback(()=>{
    if(!navigator.onLine)return;
    getHealth().then(()=>"up" as const).catch((e:ApiError)=>(e.kind==="network"?"down":"up") as "up"|"down").then(next=>{
      const was=lastBackend.current;lastBackend.current=next;setBackend(next);
      if(next==="up"&&was==="down"){setEpoch(n=>n+1);refreshAi();void synchronize();}
    });
  },[refreshAi]);
  useEffect(()=>{
    checkBackend();const timer=setInterval(checkBackend,15000);
    window.addEventListener("online",checkBackend);window.addEventListener("focus",checkBackend);
    return ()=>{clearInterval(timer);window.removeEventListener("online",checkBackend);window.removeEventListener("focus",checkBackend);};
  },[checkBackend]);

  const value=useMemo(()=>({profile,setProfile,online,sync,conflicts,removeConflict,events,ai,refreshAi,backend,epoch,checkBackend}),[profile,setProfile,online,sync,conflicts,removeConflict,events,ai,refreshAi,backend,epoch,checkBackend]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
