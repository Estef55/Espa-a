import {test} from "node:test";
import assert from "node:assert/strict";
import {can,denialMessage} from "../src/lib/permissions.ts";
import {ROUTES,parseHash,routeLabel} from "../src/lib/router.ts";
import {buildSubmissionsCsv,csvCell} from "../src/lib/csv.ts";
import {dateLabel,formatBytes,fromLocalInput,isSafeResourceUrl,toLocalInput} from "../src/lib/format.ts";
import {conflictFromEvent,planResolution,type SyncConflict} from "../src/lib/conflicts.ts";
import {loadUploads,removeUpload,upsertUpload} from "../src/lib/uploadIndex.ts";
import {adaptationToText} from "../src/lib/quiz.ts";

test("permisos coinciden con el backend: lo docente excluye a admin y estudiante",()=>{
  for(const f of ["materials.upload","documents","chat","preferences","reports"] as const){assert.ok(can("teacher",f));assert.ok(!can("admin",f));assert.ok(!can("student",f));}
  assert.ok(can("admin","assignments.write")&&can("teacher","submissions.review")&&!can("student","assignments.write"));
  assert.ok(can("student","submissions.send")&&!can("teacher","submissions.send"));
  assert.match(denialMessage("student","documents"),/solo para el perfil docente/);
});
test("navegación: hash → ruta, con valor por defecto",()=>{
  assert.equal(parseHash("#/actividades"),"actividades");assert.equal(parseHash("#/documentos?id=1"),"documentos");
  assert.equal(parseHash(""),"inicio");assert.equal(parseHash("#/inexistente"),"inicio");
  assert.equal(new Set(ROUTES.map(r=>r.id)).size,ROUTES.length);
  assert.equal(routeLabel("entregas","student"),"Mis entregas");assert.equal(routeLabel("entregas","teacher"),"Entregas recibidas");
});
test("CSV neutraliza fórmulas y escapa comillas",()=>{
  assert.equal(csvCell("=1+1"),`"'=1+1"`);assert.equal(csvCell("dijo \"hola\""),`"dijo ""hola"""`);
  const csv=buildSubmissionsCsv([{id:"s",assignment_id:"a1",student_id:"est",answer:"@cmd",status:"reviewed",server_version:2}],id=>id==="a1"?"Tarea":undefined);
  assert.ok(csv.startsWith("\uFEFF"));assert.match(csv,/"est";"Tarea";"'@cmd";"Revisada";"2"/);
});
test("formatos de fecha, tamaño y URL",()=>{
  assert.equal(dateLabel(null,"Sin fecha"),"Sin fecha");assert.equal(dateLabel("texto raro"),"texto raro");
  assert.notEqual(dateLabel("2026-10-01 12:00:00"),"2026-10-01 12:00:00"); // fecha SQLite (UTC) interpretada
  assert.equal(formatBytes(512),"512 B");assert.equal(formatBytes(2048),"2.0 KB");assert.equal(formatBytes(-1),"—");
  assert.equal(fromLocalInput(""),null);assert.equal(toLocalInput(fromLocalInput("2026-10-30T08:15")),"2026-10-30T08:15");
  assert.ok(isSafeResourceUrl("/materiales/a.pdf")&&isSafeResourceUrl("https://x.org/a"));
  assert.ok(!isSafeResourceUrl("javascript:alert(1)")&&!isSafeResourceUrl("//evil.com")&&!isSafeResourceUrl("data:text/html,x"));
});
const op={operation_id:"op1",entity_id:"a1",payload:{assignment_id:"a1",answer:"mía",base_version:1,client_updated_at:"x"}};
const server={id:"s1",assignment_id:"a1",student_id:"e",answer:"servidor",status:"submitted",server_version:5};
test("conflictos: interpretación del evento y plan de resolución",()=>{
  assert.equal(conflictFromEvent(null),null);assert.equal(conflictFromEvent({}),null);
  const c=conflictFromEvent({status:"conflict",operation:op,server}) as SyncConflict;assert.equal(c.server?.server_version,5);
  assert.deepEqual(planResolution(c,"server"),{removeOperationId:"op1"});
  assert.deepEqual(planResolution(c,"local"),{removeOperationId:"op1",requeue:{assignmentId:"a1",answer:"mía",baseVersion:5}});
  const sinServidor:SyncConflict={operation:op};
  assert.equal(planResolution(sinServidor,"local").missingServerVersion,true);
  assert.equal(planResolution(sinServidor,"local",7).requeue?.baseVersion,7);
});
test("índice local de materiales subidos: por usuario, sin duplicados, tolera datos corruptos",()=>{
  const mem=new Map<string,string>();const st={getItem:(k:string)=>mem.get(k)??null,setItem:(k:string,v:string)=>void mem.set(k,v)};
  const m=(id:string)=>({id,filename:id+".txt",content_type:"text/plain",size:1,sha256:"h",extracted_at:null,created_at:"x"});
  upsertUpload("u1",m("a"),st);upsertUpload("u1",m("b"),st);upsertUpload("u1",m("a"),st);
  assert.deepEqual(loadUploads("u1",st).map(x=>x.id),["a","b"]);assert.deepEqual(loadUploads("u2",st),[]);
  assert.deepEqual(removeUpload("u1","a",st).map(x=>x.id),["b"]);
  mem.set("pacha-uploads:u3","{no json");assert.deepEqual(loadUploads("u3",st),[]);
});
test("adaptaciones a texto plano",()=>{
  assert.equal(adaptationToText("resumen"),"resumen");
  assert.equal(adaptationToText([{id:1,type:"open",question:"¿Qué?",reference_fragment:"",topic_hint:"",answer_key:null,teacher_review_required:true}]),"1. ¿Qué?");
});
