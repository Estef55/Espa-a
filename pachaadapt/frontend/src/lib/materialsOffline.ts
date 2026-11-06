// Copia local de materiales del docente (lista, detalle, original). La lógica es independiente del almacén: recibe una interfaz.
import type { AdaptationRecord, MaterialInfo, OrganizedText } from "./materials.types.ts";

export interface KV {
  putCache(key: string, value: unknown): Promise<unknown>;
  getCacheEntry<T>(key: string): Promise<{ value: T; saved_at: string } | undefined>;
  putAsset(key: string, blob: Blob): Promise<unknown>;
  getAsset(key: string): Promise<Blob | undefined>;
}
export type Detail = { material: MaterialInfo; adaptations: AdaptationRecord[]; text: OrganizedText | null };
// Las claves incluyen al usuario: dos perfiles en el mismo navegador no comparten copias.
export const listKey = (user: string) => `i2:list:${user}`;
export const detailKey = (user: string, id: string) => `i2:detail:${user}:${id}`;
export const originalKey = (user: string, id: string) => `i2:orig:${user}:${id}`;
export const draftKey = (user: string, assignmentId: string) => `i2:draft:${user}:${assignmentId}`;

export async function saveList(kv: KV, user: string, list: MaterialInfo[]) { await kv.putCache(listKey(user), list); }
export const loadList = (kv: KV, user: string) => kv.getCacheEntry<MaterialInfo[]>(listKey(user));
export async function saveDetail(kv: KV, user: string, d: Detail) { await kv.putCache(detailKey(user, d.material.id), d); }
export const loadDetail = (kv: KV, user: string, id: string) => kv.getCacheEntry<Detail>(detailKey(user, id));
export const loadOriginal = (kv: KV, user: string, id: string) => kv.getAsset(originalKey(user, id));

export type Fetchers = { detail: () => Promise<Detail>; original: () => Promise<Blob> };
export type DownloadResult = { detail: boolean; original: boolean; errors: string[] };
/** Guarda para uso sin conexión. Si una parte falla, lo informa y conserva la otra (nunca finge éxito). */
export async function downloadForOffline(kv: KV, user: string, id: string, f: Fetchers): Promise<DownloadResult> {
  const out: DownloadResult = { detail: false, original: false, errors: [] };
  try { await saveDetail(kv, user, await f.detail()); out.detail = true; } catch (e) { out.errors.push(`Datos y adaptaciones: ${(e as Error).message}`); }
  try { await kv.putAsset(originalKey(user, id), await f.original()); out.original = true; } catch (e) { out.errors.push(`Archivo original: ${(e as Error).message}`); }
  return out;
}
export async function offlineState(kv: KV, user: string, id: string) {
  const [d, o] = await Promise.all([loadDetail(kv, user, id).catch(() => undefined), loadOriginal(kv, user, id).catch(() => undefined)]);
  return { detail: !!d, original: !!o, savedAt: d?.saved_at };
}
export type DraftValue = { text: string };
export async function saveDraft(kv: KV, user: string, assignmentId: string, text: string) { await kv.putCache(draftKey(user, assignmentId), { text }); }
export async function loadDraft(kv: KV, user: string, assignmentId: string): Promise<string> {
  return (await kv.getCacheEntry<DraftValue>(draftKey(user, assignmentId)).catch(() => undefined))?.value.text ?? "";
}
