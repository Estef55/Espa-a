// Pruebas del integrante 2 en el frontend: reglas de presentación, copia local sin conexión y llamadas a la API.
import {test} from "node:test";
import assert from "node:assert/strict";
import {setActor} from "../src/services/http.ts";
import {downloadOriginal,exportAdaptation,getCapabilities,getMaterialText,linkAdaptation,listAdaptations,listMaterials,reviewAdaptation} from "../src/services/materials.service.ts";
import {adaptationBadge,canGenerate,connectionNeeds,groupByKind,kindAvailability,NOT_IMPLEMENTED,offlineSummary,resourceOffline} from "../src/lib/materialsView.ts";
import {downloadForOffline,loadDetail,loadDraft,loadList,loadOriginal,offlineState,saveDraft,saveList,draftKey,detailKey} from "../src/lib/materialsOffline.ts";
import type {KV} from "../src/lib/materialsOffline.ts";
import type {AdaptationRecord,Capabilities,MaterialInfo} from "../src/lib/materials.types.ts";

const caps:Capabilities={formats:[".pdf",".txt"],max_upload_bytes:1,features:{
  summary:{available:true,reason:null,needs_internet:false},easy_read:{available:true,reason:null,needs_internet:false},
  outline:{available:true,reason:null,needs_internet:false},quiz:{available:true,reason:null,needs_internet:false},
  image_notes:{available:true,reason:null,needs_internet:false},audio:{available:false,reason:"No hay un motor de voz local",needs_internet:false},
  ocr:{available:false,reason:"Falta Tesseract",needs_internet:false}}};
const mat=(over:Partial<MaterialInfo>={}):MaterialInfo=>({id:"a".repeat(32),filename:"x.pdf",content_type:"application/pdf",size:1,sha256:"h",created_at:"2026-01-01",extracted_at:null,status:"uploaded",method:null,attempts:0,error:null,page_count:null,image_count:null,warnings:[],is_demo:false,adaptation_count:0,...over});
function memory():KV&{cache:Map<string,unknown>;assets:Map<string,Blob>}{
  const cache=new Map<string,unknown>(),assets=new Map<string,Blob>();
  return {cache,assets,
    putCache:async(k,v)=>{cache.set(k,{value:v,saved_at:"2026-01-01T00:00:00Z"});},
    getCacheEntry:async<T>(k:string)=>cache.get(k) as {value:T;saved_at:string}|undefined,
    putAsset:async(k,b)=>{assets.set(k,b);},getAsset:async k=>assets.get(k)};
}

test("disponibilidad: sin información del servidor se considera NO disponible",()=>{
  assert.equal(kindAvailability(null,"summary").available,false);
  assert.equal(kindAvailability(caps,"summary").available,true);
  const audio=kindAvailability(caps,"audio");assert.equal(audio.available,false);assert.match(audio.reason,/motor de voz/);
});
test("capacidades: lo local no pide Internet y lo no implementado nunca se ofrece",()=>{
  const rows=connectionNeeds(caps);
  assert.ok(rows.every(r=>!r.needsInternet));
  assert.equal(rows.find(r=>r.label.includes("OCR"))?.ok,false);
  assert.ok(NOT_IMPLEMENTED.some(x=>/Traducción/.test(x))&&NOT_IMPLEMENTED.some(x=>/quechua/i.test(x)));
});
test("insignias: parcial y sin revisar nunca se presentan como completas y revisadas",()=>{
  assert.match(adaptationBadge({status:"partial",review_status:"pending"}).text,/Parcial · sin revisar/);
  assert.match(adaptationBadge({status:"complete",review_status:"pending"}).text,/pendiente de revisión/);
  assert.equal(adaptationBadge({status:"complete",review_status:"approved"}).tone,"ok");
});
test("generar: solo con texto extraído",()=>{
  assert.equal(canGenerate(mat({status:"extracted"})),null);
  for(const s of ["uploaded","no_text","failed"] as const)assert.ok(canGenerate(mat({status:s})));
});
test("disponibilidad sin conexión por material",()=>{
  assert.equal(resourceOffline({detail:true,original:true}).level,"full");
  assert.equal(resourceOffline({detail:true,original:false}).level,"partial");
  assert.equal(resourceOffline({detail:false,original:false}).level,"none");
  assert.match(offlineSummary([{level:"full"},{level:"none"},{level:"partial"}]),/1 de 3.*1 parcialmente/);
});
test("agrupar adaptaciones por tipo conserva el orden",()=>{
  const g=groupByKind([{adaptation:"quiz"},{adaptation:"summary"},{adaptation:"summary"}] as AdaptationRecord[]);
  assert.deepEqual(g.map(x=>[x.kind,x.items.length]),[["summary",2],["quiz",1]]);
});

test("copia local: lista y detalle separados por usuario",async()=>{
  const kv=memory();
  await saveList(kv,"t1",[mat()]);
  assert.equal((await loadList(kv,"t1"))?.value.length,1);
  assert.equal(await loadList(kv,"t2"),undefined);
  assert.notEqual(detailKey("t1","x"),detailKey("t2","x"));
});
test("guardar para uso sin conexión: éxito total",async()=>{
  const kv=memory();const m=mat({status:"extracted"});
  const r=await downloadForOffline(kv,"t1",m.id,{detail:async()=>({material:m,adaptations:[],text:null}),original:async()=>new Blob(["%PDF"])});
  assert.deepEqual([r.detail,r.original,r.errors.length],[true,true,0]);
  assert.deepEqual(await offlineState(kv,"t1",m.id),{detail:true,original:true,savedAt:"2026-01-01T00:00:00Z"});
  assert.ok(await loadOriginal(kv,"t1",m.id));assert.ok(await loadDetail(kv,"t1",m.id));
});
test("guardar para uso sin conexión: si falla una parte lo dice y conserva la otra",async()=>{
  const kv=memory();const m=mat();
  const r=await downloadForOffline(kv,"t1",m.id,{detail:async()=>({material:m,adaptations:[],text:null}),original:async()=>{throw new Error("sin conexión");}});
  assert.deepEqual([r.detail,r.original],[true,false]);assert.match(r.errors[0],/Archivo original: sin conexión/);
  const s=await offlineState(kv,"t1",m.id);assert.equal(s.detail,true);assert.equal(s.original,false);
});
test("borrador de respuesta: se recupera y es por usuario y actividad",async()=>{
  const kv=memory();
  await saveDraft(kv,"est1","as1","Mi respuesta a medias");
  assert.equal(await loadDraft(kv,"est1","as1"),"Mi respuesta a medias");
  assert.equal(await loadDraft(kv,"est1","as2"),"");assert.equal(await loadDraft(kv,"est2","as1"),"");
  await saveDraft(kv,"est1","as1","");assert.equal(await loadDraft(kv,"est1","as1"),"");
  assert.notEqual(draftKey("a","b"),draftKey("a","c"));
});

type Call={method:string;path:string;search:string;body:unknown};
function record(response:unknown={}){
  const calls:Call[]=[];
  globalThis.fetch=(async(url:URL|string,init:RequestInit={})=>{
    const u=new URL(String(url));const raw=init.body;
    calls.push({method:init.method??"GET",path:u.pathname,search:u.search,body:typeof raw==="string"?JSON.parse(raw):raw});
    return response instanceof Blob?new Response(response,{status:200,headers:{"Content-Disposition":'attachment; filename="doc.pdf"'}}):new Response(JSON.stringify(response),{status:200});
  }) as typeof fetch;
  return calls;
}
test("servicios de materiales llaman a los endpoints del backend",async()=>{
  setActor("demo-teacher","teacher");const id="a".repeat(32),aid="b".repeat(32);const calls=record([]);
  await listMaterials();await getCapabilities();await getMaterialText(id);await listAdaptations(id);
  await reviewAdaptation(id,aid,true);await linkAdaptation(id,aid,"assignment","as1");await exportAdaptation(id,aid,"txt");
  assert.deepEqual(calls.map(c=>[c.method,c.path+c.search]),[
    ["GET","/api/v1/materials"],["GET","/api/v1/materials/capabilities"],["GET",`/api/v1/materials/${id}/text`],["GET",`/api/v1/materials/${id}/adaptations`],
    ["POST",`/api/v1/materials/${id}/adaptations/${aid}/review`],["POST",`/api/v1/materials/${id}/adaptations/${aid}/links`],
    ["GET",`/api/v1/materials/${id}/adaptations/${aid}/export?format=txt`]]);
  assert.deepEqual(calls[4].body,{approved:true});assert.deepEqual(calls[5].body,{target_type:"assignment",target_id:"as1"});
});
test("descarga del original devuelve el archivo y su nombre; un error del servidor se informa",async()=>{
  record(new Blob(["%PDF"]));
  const r=await downloadOriginal("a".repeat(32));assert.equal(r.filename,"doc.pdf");assert.equal(await r.blob.text(),"%PDF");
  globalThis.fetch=(async()=>new Response(JSON.stringify({detail:"Material no encontrado."}),{status:404})) as typeof fetch;
  await assert.rejects(()=>downloadOriginal("a".repeat(32)),(e:Error)=>/no encontrado/.test(e.message));
  globalThis.fetch=(async()=>{throw new TypeError("fetch failed");}) as typeof fetch;
  await assert.rejects(()=>downloadOriginal("a".repeat(32)),(e:{kind?:string})=>e.kind==="network");
});
