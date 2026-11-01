// El backend no tiene endpoint para LISTAR materiales subidos (solo GET por id). Este índice local, por perfil y
// por navegador, recuerda los identificadores subidos desde aquí; cada ficha se consulta al servidor al abrirla.
import type {UploadedMaterial} from "./types.ts";
type KV=Pick<Storage,"getItem"|"setItem">;
const MAX_ITEMS=100;
const key=(user:string)=>`pacha-uploads:${user}`;

export function loadUploads(user:string,storage:KV|undefined=globalThis.localStorage):UploadedMaterial[]{
  try{
    const parsed=JSON.parse(storage?.getItem(key(user))??"[]");
    return Array.isArray(parsed)?parsed.filter((x):x is UploadedMaterial=>!!x&&typeof x.id==="string"&&typeof x.filename==="string"):[];
  }catch{return [];}
}
function save(user:string,items:UploadedMaterial[],storage:KV|undefined){try{storage?.setItem(key(user),JSON.stringify(items.slice(0,MAX_ITEMS)));}catch{/* almacenamiento lleno o bloqueado */}}
export function upsertUpload(user:string,item:UploadedMaterial,storage:KV|undefined=globalThis.localStorage):UploadedMaterial[]{
  const next=[item,...loadUploads(user,storage).filter(x=>x.id!==item.id)];save(user,next,storage);return next.slice(0,MAX_ITEMS);
}
export function removeUpload(user:string,id:string,storage:KV|undefined=globalThis.localStorage):UploadedMaterial[]{
  const next=loadUploads(user,storage).filter(x=>x.id!==id);save(user,next,storage);return next;
}
