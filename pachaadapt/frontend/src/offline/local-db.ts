const DB_NAME = "pachaadapt-offline";
const DB_VERSION = 2;
export type PendingOperation = {
  operation_id: string; entity_type: "submission"; entity_id: string;
  payload: {assignment_id:string;answer:string;base_version:number;client_updated_at:string}; created_at: string; attempts: number;
  /** Perfil que creó la operación. Opcional: las operaciones guardadas por versiones anteriores no lo tienen. */
  actor?: {id:string;role:string};
};
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve,reject) => {
    const request=indexedDB.open(DB_NAME,DB_VERSION);
    request.onupgradeneeded=()=> {
      const db=request.result;
      if(!db.objectStoreNames.contains("queue")) db.createObjectStore("queue",{keyPath:"operation_id"});
      if(!db.objectStoreNames.contains("cache")) db.createObjectStore("cache",{keyPath:"key"});
      if(!db.objectStoreNames.contains("meta")) db.createObjectStore("meta",{keyPath:"key"});
      if(!db.objectStoreNames.contains("assets")) db.createObjectStore("assets",{keyPath:"key"});
    };
    request.onsuccess=()=>resolve(request.result); request.onerror=()=>reject(request.error);
  });
}
async function store<T>(name:string, mode:IDBTransactionMode, action:(s:IDBObjectStore)=>IDBRequest):Promise<T>{
  const db=await openDB();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(name,mode), req=action(tx.objectStore(name));
    req.onsuccess=()=>resolve(req.result as T); req.onerror=()=>reject(req.error);
    tx.oncomplete=()=>db.close(); tx.onerror=()=>reject(tx.error);
  });
}
export const localDB = {
  enqueue:(op:PendingOperation)=>store("queue","readwrite",s=>s.put(op)),
  remove:(id:string)=>store("queue","readwrite",s=>s.delete(id)),
  all:()=>store<PendingOperation[]>("queue","readonly",s=>s.getAll()),
  putCache:(key:string,value:unknown)=>store("cache","readwrite",s=>s.put({key,value,saved_at:new Date().toISOString()})),
  getCache:<T>(key:string)=>store<{key:string,value:T}|undefined>("cache","readonly",s=>s.get(key)).then(x=>x?.value),
  getCacheEntry:<T>(key:string)=>store<{key:string,value:T,saved_at:string}|undefined>("cache","readonly",s=>s.get(key)),
  putAsset:(key:string,blob:Blob)=>store("assets","readwrite",s=>s.put({key,blob,saved_at:new Date().toISOString()})),
  getAsset:(key:string)=>store<{key:string,blob:Blob}|undefined>("assets","readonly",s=>s.get(key)).then(x=>x?.blob),
  count:()=>localDB.all().then(x=>x.length)
};
