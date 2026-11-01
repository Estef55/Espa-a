import {useEffect,useState} from "react";
import {localDB,type PendingOperation} from "../offline/local-db";
import {belongsToCurrentActor} from "../offline/sync-queue";
import {useApp} from "../context";

/** Operaciones de la cola offline del perfil activo (se recargan cuando cambia el estado de sincronización). */
export function usePendingOps():PendingOperation[]{
  const {sync,profile}=useApp();
  const [ops,setOps]=useState<PendingOperation[]>([]);
  useEffect(()=>{
    let active=true;
    localDB.all().then(all=>{if(active)setOps(all.filter(belongsToCurrentActor));}).catch(()=>{if(active)setOps([]);});
    return ()=>{active=false;};
  },[sync.pending,sync.syncing,profile.user,profile.role]);
  return ops;
}
