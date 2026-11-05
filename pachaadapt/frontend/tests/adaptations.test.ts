import { test } from "node:test";
import assert from "node:assert/strict";
import { setActor } from "../src/services/http.ts";
import * as svc from "../src/services/adaptations.service.ts";
import {MemoryKV,saveAdaptation,getAdaptation,listAdaptations,deleteAdaptation,saveDraft,getDraft,clearDraft,listDrafts,saveDocumentDraft,getDocumentDraft,clearDocumentDraft,saveDocumentList,getDocumentList,saveDocumentSnapshot,getDocumentSnapshot} from "../src/offline/adaptation-store.ts";
import { OFFLINE_ON_DEVICE, splitByConnection, describeResource } from "../src/lib/resources.ts";

setActor("demo-teacher", "teacher");
function record() {
  const calls: { method: string; path: string; body: unknown }[] = [];
  globalThis.fetch = (async (url: URL | string, init: RequestInit = {}) => {
    calls.push({ method: init.method ?? "GET", path: new URL(String(url)).pathname, body: typeof init.body === "string" ? JSON.parse(init.body) : init.body });
    return new Response("{}", { status: 200 });
  }) as typeof fetch; return calls;
}
test("servicio de adaptaciones llama a los endpoints esperados", async () => {
  const c = record(); const id = "a".repeat(32);
  await svc.getCapabilities(); await svc.buildVisual(id, "concept_map"); await svc.buildAccessible(id, "braille");
  await svc.buildAudioScript(id); await svc.buildAudio(id); await svc.translateMaterial(id, "qu"); await svc.describeImage("AAAA"); await svc.subtitlesToText("x");
  assert.deepEqual(c.map(x => x.path), ["/api/v1/adaptations/capabilities", `/api/v1/adaptations/materials/${id}/visual`, `/api/v1/adaptations/materials/${id}/accessible`,
    `/api/v1/adaptations/materials/${id}/audio-script`, `/api/v1/adaptations/materials/${id}/audio`, `/api/v1/adaptations/materials/${id}/translate`, "/api/v1/adaptations/images/describe", "/api/v1/adaptations/subtitles"]);
  assert.deepEqual(c[5].body, { target: "qu", source: "es" });
});
test("501 se informa como capacidad no disponible", async () => {
  globalThis.fetch = (async () => new Response(JSON.stringify({ detail: "No hay motor" }), { status: 501 })) as typeof fetch;
  await assert.rejects(svc.buildAudio("a".repeat(32)), (e: { kind?: string }) => e.kind === "not_implemented");
});
test("adaptaciones guardadas se conservan y se aíslan por usuario", async () => {
  const s = new MemoryKV();
  await saveAdaptation("u1", "m1", "summary", "texto", true, s); await saveAdaptation("u2", "m1", "summary", "otro", true, s);
  assert.equal((await getAdaptation("u1", "m1", "summary", s))?.content, "texto");
  assert.equal((await listAdaptations("u1", undefined, s)).length, 1);
  await deleteAdaptation("u1", "m1", "summary", s); assert.equal(await getAdaptation("u1", "m1", "summary", s), undefined);
  assert.equal((await getAdaptation("u2", "m1", "summary", s))?.content, "otro");
});
test("borradores de actividad: guardar, recuperar y borrar solo al confirmar", async () => {
  const s = new MemoryKV();
  await saveDraft("u1", "a1", "mi respuesta", s); assert.equal((await getDraft("u1", "a1", s))?.answer, "mi respuesta");
  assert.equal((await listDrafts("u1", s)).length, 1); assert.equal((await listDrafts("u2", s)).length, 0);
  await saveDraft("u1", "a1", "  ", s); assert.equal(await getDraft("u1", "a1", s), undefined);
  await saveDraft("u1", "a2", "x", s); await clearDraft("u1", "a2", s); assert.equal(await getDraft("u1", "a2", s), undefined);
});
test("borradores de documentos se aíslan por docente y solo se limpian tras guardar en servidor",async()=>{
  const s=new MemoryKV();
  await saveDocumentDraft("t1","d1","cambios locales",2,s);
  const draft=await getDocumentDraft("t1","d1",s);assert.equal(draft?.content,"cambios locales");assert.equal(draft?.base_version,2);
  assert.equal(await getDocumentDraft("t2","d1",s),undefined);
  await clearDocumentDraft("t1","d1",s);assert.equal(await getDocumentDraft("t1","d1",s),undefined);
  const docs=[{id:"d1",title:"Guía"}];await saveDocumentList("t1",false,docs,s);await saveDocumentSnapshot("t1","d1",{...docs[0],content:"base"},s);
  assert.deepEqual(await getDocumentList("t1",false,s),docs);assert.equal((await getDocumentSnapshot<{content:string}>("t1","d1",s))?.content,"base");
  assert.equal(await getDocumentList("t2",false,s),undefined);
});
test("recursos: separación offline / con conexión",()=>{
  const r = [...OFFLINE_ON_DEVICE, { id: "t", label: "Traducción", available: false, requires_server: true, requires_internet: true, works_offline_on_device: false, note: "Sin proveedor" }];
  const { offline, needsConnection } = splitByConnection(r);
  assert.equal(offline.length, 3); assert.equal(needsConnection.length, 1);
  assert.equal(describeResource(r[3], true), "Sin proveedor"); assert.equal(describeResource(r[0], false), "Disponible sin conexión");
});
