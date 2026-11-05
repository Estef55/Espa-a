// Conserva en el dispositivo (a) adaptaciones generadas y guardadas y (b) borradores de actividades,
// para que no se pierdan al desconectarse. Es un almacén APARTE (no toca la cola de sincronización de
// offline/local-db.ts): un borrador NO es una entrega y no se envía al servidor desde aquí.
export type StoredAdaptation = { key: string; user: string; material_id: string; kind: string; content: unknown; saved_at: string; review_required: boolean };
export type ActivityDraft = { key: string; user: string; assignment_id: string; answer: string; updated_at: string };
export type DocumentDraft = { key:string;user:string;document_id:string;content:string;base_version:number;updated_at:string };
export interface KV { get<T>(key: string): Promise<T | undefined>; put(key: string, value: unknown): Promise<void>; del(key: string): Promise<void>; keys(prefix: string): Promise<string[]> }

export class MemoryKV implements KV {
  private m = new Map<string, unknown>();
  async get<T>(k: string) { return this.m.get(k) as T | undefined; }
  async put(k: string, v: unknown) { this.m.set(k, structuredClone(v)); }
  async del(k: string) { this.m.delete(k); }
  async keys(p: string) { return [...this.m.keys()].filter(k => k.startsWith(p)); }
}

/** IndexedDB propio: base «pachaadapt-adaptations» (independiente de «pachaadapt-offline»). */
export class IndexedKV implements KV {
  private db?: Promise<IDBDatabase>;
  private open() {
    this.db ??= new Promise((res, rej) => {
      const r = indexedDB.open("pachaadapt-adaptations", 1);
      r.onupgradeneeded = () => { r.result.createObjectStore("kv"); };
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
    return this.db;
  }
  private async run<T>(mode: IDBTransactionMode, f: (s: IDBObjectStore) => IDBRequest): Promise<T> {
    const db = await this.open();
    return new Promise((res, rej) => { const q = f(db.transaction("kv", mode).objectStore("kv")); q.onsuccess = () => res(q.result as T); q.onerror = () => rej(q.error); });
  }
  get<T>(k: string) { return this.run<T | undefined>("readonly", s => s.get(k)); }
  async put(k: string, v: unknown) { await this.run("readwrite", s => s.put(v, k)); }
  async del(k: string) { await this.run("readwrite", s => s.delete(k)); }
  async keys(p: string) { return (await this.run<IDBValidKey[]>("readonly", s => s.getAllKeys())).map(String).filter(k => k.startsWith(p)); }
}

let defaultKV: KV | undefined;
const kv = (): KV => (defaultKV ??= typeof indexedDB !== "undefined" ? new IndexedKV() : new MemoryKV());
export function useKV(custom?: KV) { defaultKV = custom; }

const adKey = (user: string, material: string, kind: string) => `adaptation:${user}:${material}:${kind}`;
const drKey = (user: string, assignment: string) => `draft:${user}:${assignment}`;
const docDrKey = (user:string,document:string) => `document-draft:${user}:${document}`;

export async function saveAdaptation(user: string, material_id: string, kind: string, content: unknown, review_required = true, store: KV = kv()) {
  const rec: StoredAdaptation = { key: adKey(user, material_id, kind), user, material_id, kind, content, review_required, saved_at: new Date().toISOString() };
  await store.put(rec.key, rec); return rec;
}
export const getAdaptation = (user: string, material_id: string, kind: string, store: KV = kv()) => store.get<StoredAdaptation>(adKey(user, material_id, kind));
export async function listAdaptations(user: string, material_id?: string, store: KV = kv()) {
  const keys = await store.keys(`adaptation:${user}:${material_id ? material_id + ":" : ""}`);
  return (await Promise.all(keys.map(k => store.get<StoredAdaptation>(k)))).filter((x): x is StoredAdaptation => !!x);
}
export const deleteAdaptation = (user: string, material_id: string, kind: string, store: KV = kv()) => store.del(adKey(user, material_id, kind));

/** Guarda el texto en curso de una actividad (llamar al escribir). Un borrador vacío se elimina. */
export async function saveDraft(user: string, assignment_id: string, answer: string, store: KV = kv()) {
  if (!answer.trim()) { await store.del(drKey(user, assignment_id)); return undefined; }
  const rec: ActivityDraft = { key: drKey(user, assignment_id), user, assignment_id, answer, updated_at: new Date().toISOString() };
  await store.put(rec.key, rec); return rec;
}
export const getDraft = (user: string, assignment_id: string, store: KV = kv()) => store.get<ActivityDraft>(drKey(user, assignment_id));
/** Borrar SOLO cuando el servidor confirmó la entrega (nunca al iniciar el envío). */
export const clearDraft = (user: string, assignment_id: string, store: KV = kv()) => store.del(drKey(user, assignment_id));
export async function listDrafts(user: string, store: KV = kv()) {
  const keys = await store.keys(`draft:${user}:`);
  return (await Promise.all(keys.map(k => store.get<ActivityDraft>(k)))).filter((x): x is ActivityDraft => !!x);
}

/** Persists unsubmitted document edits on this device; never enqueues or marks them as synced. */
export async function saveDocumentDraft(user:string,document_id:string,content:string,base_version:number,store:KV=kv()) {
  const rec:DocumentDraft={key:docDrKey(user,document_id),user,document_id,content,base_version,updated_at:new Date().toISOString()};
  await store.put(rec.key,rec);return rec;
}
export const getDocumentDraft=(user:string,document_id:string,store:KV=kv())=>store.get<DocumentDraft>(docDrKey(user,document_id));
/** Delete only after the server accepted the corresponding version. */
export const clearDocumentDraft=(user:string,document_id:string,store:KV=kv())=>store.del(docDrKey(user,document_id));
const docListKey=(user:string,includeArchived:boolean)=>`document-list:${user}:${includeArchived?"archived":"active"}`;
const docSnapshotKey=(user:string,document_id:string)=>`document-snapshot:${user}:${document_id}`;
/** Last server-confirmed document summaries used only to reopen owned documents without a network. */
export const saveDocumentList=(user:string,includeArchived:boolean,documents:unknown[],store:KV=kv())=>store.put(docListKey(user,includeArchived),documents);
export const getDocumentList=<T=unknown>(user:string,includeArchived:boolean,store:KV=kv())=>store.get<T[]>(docListKey(user,includeArchived));
/** Last server-confirmed content becomes the base for offline drafts and conflict comparison. */
export const saveDocumentSnapshot=(user:string,document_id:string,document:unknown,store:KV=kv())=>store.put(docSnapshotKey(user,document_id),document);
export const getDocumentSnapshot=<T=unknown>(user:string,document_id:string,store:KV=kv())=>store.get<T>(docSnapshotKey(user,document_id));
