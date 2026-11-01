import {localDB} from "./local-db";
import {API,networkError,toApiError} from "../services/http";

export type Cached<T>={data:T;fromCache:boolean;savedAt?:string};
// Los 4xx (permisos, validación) NO deben ocultarse con datos guardados; los fallos de red o 5xx sí usan la copia local.

async function loadWithCache<T>(key:string,url:string,headers:Record<string,string>,after?:(data:T)=>Promise<void>):Promise<Cached<T>>{
  try{
    let response:Response;
    try{response=await fetch(url,{headers});}catch{throw networkError();}
    if(!response.ok)throw await toApiError(response);
    const data=await response.json() as T;
    await localDB.putCache(key,data);
    if(after)await after(data);
    return {data,fromCache:false};
  }catch(error){
    const status=(error as {status?:number}).status;const clientError=typeof status==="number"&&status>=400&&status<500;
    if(!clientError){
      const entry=await localDB.getCacheEntry<T>(key).catch(()=>undefined);
      if(entry)return {data:entry.value,fromCache:true,savedAt:entry.saved_at};
    }
    throw error;
  }
}
async function prefetchAssets(materials:{id:string;resource_url:string}[]){
  await Promise.all(materials.map(async material=>{
    try{
      const url=new URL(material.resource_url,window.location.origin);
      if(url.origin!==window.location.origin)return;
      const file=await fetch(url.toString());
      if(file.ok)await localDB.putAsset(material.id,await file.blob());
    }catch{/* Mantener el registro y volver a intentar cuando haya conexión. */}
  }));
}
// Las claves de caché incluyen el usuario para no mezclar datos entre perfiles de demostración.
const cacheKey=(name:string,headers:Record<string,string>)=>`${name}:${headers["X-User-Id"]??"anon"}:${headers["X-Role"]??""}`;
export const loadAssignments=(headers:Record<string,string>={})=>loadWithCache<unknown[]>(cacheKey("assignments",headers),`${API}/api/v1/assignments`,headers);
export const loadMaterials=(headers:Record<string,string>={})=>loadWithCache<{id:string;resource_url:string}[]>(cacheKey("materials",headers),`${API}/api/v1/material-library`,headers,prefetchAssets);
// Funciones originales (se conservan por compatibilidad): devuelven solo los datos.
export async function cacheAssignments(headers:Record<string,string>={}){return (await loadAssignments(headers)).data;}
export async function cacheMaterials(headers:Record<string,string>={}){return (await loadMaterials(headers)).data;}
