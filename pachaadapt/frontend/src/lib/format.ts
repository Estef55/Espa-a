// Utilidades de presentación (español, Perú).
export const STATUS_LABEL: Record<string,string>={published:"Publicada",draft:"Borrador",closed:"Cerrada",submitted:"Entregada",reviewed:"Revisada",returned:"Devuelta",ok:"Completo",insufficient_data:"Datos insuficientes"};
export const statusLabel=(value:string)=>STATUS_LABEL[value]??value;

export function dateLabel(value?:string|null,empty="Sin fecha"):string{
  if(!value)return empty;
  // SQLite devuelve "YYYY-MM-DD HH:MM:SS" en UTC sin zona: se interpreta como UTC.
  const iso=/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)?value.replace(" ","T")+"Z":value;
  const date=new Date(iso);
  return Number.isNaN(date.getTime())?value:date.toLocaleString("es-PE",{dateStyle:"medium",timeStyle:"short"});
}
export function formatBytes(bytes:number):string{
  if(!Number.isFinite(bytes)||bytes<0)return "—";
  if(bytes<1024)return `${bytes} B`;
  if(bytes<1024*1024)return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/1024/1024).toFixed(1)} MB`;
}
/** ISO → valor para <input type="datetime-local"> en hora local. */
export function toLocalInput(value?:string|null):string{
  if(!value)return "";
  const date=new Date(value);if(Number.isNaN(date.getTime()))return "";
  const p=(n:number)=>String(n).padStart(2,"0");
  return `${date.getFullYear()}-${p(date.getMonth()+1)}-${p(date.getDate())}T${p(date.getHours())}:${p(date.getMinutes())}`;
}
export const fromLocalInput=(value:string):string|null=>value?new Date(value).toISOString():null;
/** Solo http(s) o rutas locales: evita abrir esquemas como javascript:. */
export function isSafeResourceUrl(value:string):boolean{
  if(value.startsWith("/")&&!value.startsWith("//"))return true;
  try{const u=new URL(value);return u.protocol==="http:"||u.protocol==="https:";}catch{return false;}
}
