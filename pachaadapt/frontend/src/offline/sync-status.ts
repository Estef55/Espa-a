import {localDB} from "./local-db";
import {synchronize,belongsToCurrentActor} from "./sync-queue";
export type SyncState={online:boolean;pending:number;syncing:boolean;lastSync?:string;otherProfiles?:number};
export async function getSyncState():Promise<SyncState>{
  const all=await localDB.all(),mine=all.filter(belongsToCurrentActor).length;
  return {online:navigator.onLine,pending:mine,otherProfiles:all.length-mine,syncing:false,
    lastSync:localStorage.getItem("pacha-last-sync")??undefined};
}
export async function syncNow(){await synchronize();return getSyncState();}
export function watchSyncStatus(callback:(state:SyncState)=>void){
  let active=true,syncing=false;
  const refresh=async()=>{const s=await getSyncState();if(active)callback({...s,syncing});};
  const start=()=>{syncing=true;void refresh();};
  const end=()=>{syncing=false;void refresh();};
  window.addEventListener("online",refresh);window.addEventListener("offline",refresh);
  window.addEventListener("pacha-sync-change",refresh);window.addEventListener("pacha-sync-start",start);
  window.addEventListener("pacha-sync-end",end);void refresh();
  return ()=>{active=false;window.removeEventListener("online",refresh);window.removeEventListener("offline",refresh);
    window.removeEventListener("pacha-sync-change",refresh);window.removeEventListener("pacha-sync-start",start);
    window.removeEventListener("pacha-sync-end",end);};
}
