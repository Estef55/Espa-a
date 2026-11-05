// Verifica que cada servicio llama al endpoint, método y cuerpo que expone el backend.
import {test} from "node:test";
import assert from "node:assert/strict";
import {setActor} from "../src/services/http.ts";
import {adaptMaterial,extractMaterial,getUploadedMaterial,uploadMaterial,validateUpload} from "../src/services/materials.service.ts";
import {archiveDocument,createDocument,getVersion,importDocument,listDocuments,restoreVersion,saveDocument} from "../src/services/documents.service.ts";
import {deletePreferences,getAdaptationParams,updatePreferences} from "../src/services/preferences.service.ts";
import {getAiStatus,getConversation,saveAssistantProposal,sendChat} from "../src/services/ai.service.ts";
import {createReport,getReportMarkdown,listReports} from "../src/services/reports.service.ts";
import {getServerSyncStatus,pullChanges} from "../src/services/sync.service.ts";
import {reviewSubmission} from "../src/services/review.service.ts";
import {fetchClassrooms} from "../src/services/classrooms.service.ts";
import {loadProfile,saveProfile} from "../src/services/auth.service.ts";

type Call={method:string;path:string;search:string;body:unknown;headers:Record<string,string>};
function record(response:unknown={}){
  const calls:Call[]=[];
  globalThis.fetch=(async(url:URL|string,init:RequestInit={})=>{
    const u=new URL(String(url));const raw=init.body;
    calls.push({method:init.method??"GET",path:u.pathname,search:u.search,body:typeof raw==="string"?JSON.parse(raw):raw,headers:init.headers as Record<string,string>});
    return typeof response==="string"?new Response(response):new Response(JSON.stringify(response),{status:200});
  }) as typeof fetch;
  return calls;
}
setActor("demo-teacher","teacher");

test("materiales: subir, consultar, extraer y adaptar",async()=>{
  const calls=record({});
  await uploadMaterial(new File(["hola"],"a.txt",{type:"text/plain"}));
  assert.equal(calls[0].method,"POST");assert.equal(calls[0].path,"/api/v1/materials");assert.ok(calls[0].body instanceof FormData);assert.ok((calls[0].body as FormData).get("file"));
  await getUploadedMaterial("a".repeat(32));assert.equal(calls[1].path,`/api/v1/materials/${"a".repeat(32)}`);
  await extractMaterial("b".repeat(32),true);assert.deepEqual([calls[2].method,calls[2].path,calls[2].body],["POST",`/api/v1/materials/${"b".repeat(32)}/extract`,{ocr:true}]);
  await adaptMaterial("b".repeat(32),"summary",{max_sentences:3,text:"texto"});
  assert.deepEqual(calls[3].body,{adaptation:"summary",text:"texto",options:{max_sentences:3}});
  await adaptMaterial("b".repeat(32),"quiz",{count:4});assert.deepEqual(calls[4].body,{adaptation:"quiz",options:{count:4}});
});
test("materiales: validación previa de archivo",()=>{
  assert.equal(validateUpload({name:"a.PDF",size:10}),null);
  assert.match(validateUpload({name:"a.docx",size:10})!,/PDF y TXT/);
  assert.match(validateUpload({name:"a.txt",size:0})!,/vacío/);
  assert.match(validateUpload({name:"a.txt",size:26*1024*1024})!,/25 MB/);
});
test("documentos: crear, guardar con versión esperada, restaurar, archivar, importar",async()=>{
  const calls=record({});
  await listDocuments(true);assert.equal(calls[0].search,"?include_archived=true");
  await listDocuments(false);assert.equal(calls[1].search,"");
  await createDocument({title:"T",content:"C",source_material_id:"m"});assert.deepEqual(calls[2].body,{title:"T",content:"C",source_material_id:"m"});
  await saveDocument("d1","nuevo",2,"motivo");assert.deepEqual([calls[3].method,calls[3].path,calls[3].body],["PUT","/api/v1/documents/d1",{content:"nuevo",expected_version:2,reason:"motivo"}]);
  await saveDocument("d1","nuevo",2);assert.deepEqual(calls[4].body,{content:"nuevo",expected_version:2});
  await getVersion("d1",3);assert.equal(calls[5].path,"/api/v1/documents/d1/versions/3");
  await restoreVersion("d1",1,4);assert.deepEqual([calls[6].path,calls[6].body],["/api/v1/documents/d1/restore",{version:1,expected_version:4}]);
  await archiveDocument("d1");assert.deepEqual([calls[7].method,calls[7].path],["POST","/api/v1/documents/d1/archive"]);
  await importDocument("m1");assert.deepEqual([calls[8].path,calls[8].body],["/api/v1/documents/import",{material_id:"m1"}]);
});
test("preferencias: PUT solo con lo modificado; parámetros propuestos",async()=>{
  const calls=record({});
  await updatePreferences({tone:"formal",education_level:null});assert.deepEqual([calls[0].method,calls[0].body],["PUT",{tone:"formal",education_level:null}]);
  await deletePreferences();assert.deepEqual([calls[1].method,calls[1].path,calls[1].body],["DELETE","/api/v1/preferences",undefined]);
  await getAdaptationParams();assert.equal(calls[2].path,"/api/v1/preferences/adaptation-params");
});
test("asistente: estado, chat con contexto y conversación",async()=>{
  const calls=record({});
  await getAiStatus();assert.equal(calls[0].path,"/api/v1/ai-chat/status");
  await sendChat("¿Qué dice?");assert.deepEqual(calls[1].body,{question:"¿Qué dice?"});
  await sendChat("otra","c1","d1");assert.deepEqual(calls[2].body,{question:"otra",conversation_id:"c1",document_id:"d1"});
  await getConversation("c1");assert.equal(calls[3].path,"/api/v1/ai-chat/conversations/c1");
  await saveAssistantProposal("Propuesta docente revisada","Contenido que el docente revisó.");
  assert.deepEqual([calls[4].method,calls[4].path,calls[4].body],["POST","/api/v1/documents",{title:"Propuesta docente revisada",content:"Contenido que el docente revisó."}]);
});
test("informes: criterios sin vacíos (el backend rechaza claves desconocidas), lista y markdown",async()=>{
  let calls=record({});
  await createReport({pass_threshold_pct:60,topic:"",group:undefined,date_from:"2026-01-01"});
  assert.deepEqual([calls[0].method,calls[0].path,calls[0].body],["POST","/api/v1/reports",{pass_threshold_pct:60,date_from:"2026-01-01"}]);
  await listReports();assert.equal(calls[1].path,"/api/v1/reports");
  calls=record("# Informe");assert.equal(await getReportMarkdown("r1"),"# Informe");assert.equal(calls[0].path,"/api/v1/reports/r1/markdown");
});
test("sincronización: estado y descarga de cambios con 'since'",async()=>{
  const calls=record({});
  await getServerSyncStatus();assert.equal(calls[0].path,"/api/v1/synchronization/status");
  await pullChanges("2026-10-01 00:00:00");assert.equal(calls[1].search,"?since=2026-10-01+00%3A00%3A00");
});
test("identidad: el perfil guardado inválido vuelve al de demostración",()=>{
  const mem=new Map<string,string>();const st={getItem:(k:string)=>mem.get(k)??null,setItem:(k:string,v:string)=>void mem.set(k,v)};
  assert.deepEqual(loadProfile(st),{role:"student",user:"demo-student"});
  saveProfile({role:"teacher",user:"profe.1"},st);assert.deepEqual(loadProfile(st),{role:"teacher",user:"profe.1"});
  st.setItem("pacha-user","con espacios");assert.equal(loadProfile(st).user,"demo-teacher");
  st.setItem("pacha-role","superusuario");assert.equal(loadProfile(st).role,"student");
});

test("revisión de entrega envía nota y validación explícita en el contrato del backend",async()=>{
  const calls=record({id:"s1",status:"reviewed",score:8,max_score:10,validation_status:"validated"});
  await reviewSubmission("sub 1",{status:"reviewed",score:8,max_score:10,validation_status:"validated"});
  assert.deepEqual([calls[0].method,calls[0].path,calls[0].search],[
    "PATCH","/api/v1/submissions/sub%201/review",
    "?status=reviewed&score=8&max_score=10&validation_status=validated",
  ]);
});

test("aulas: consulta el espacio del perfil al endpoint de solo lectura",async()=>{
  const calls=record([{id:"class-1",name:"Aula de prueba",teacher_id:"demo-teacher"}]);
  const rows=await fetchClassrooms();
  assert.equal(calls[0].method,"GET");
  assert.equal(calls[0].path,"/api/v1/classrooms");
  assert.equal(rows[0].name,"Aula de prueba");
});
