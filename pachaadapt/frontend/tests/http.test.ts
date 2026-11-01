import {test} from "node:test";
import assert from "node:assert/strict";
import {ApiError,ID_PATTERN,request,setActor,toApiError} from "../src/services/http.ts";

const json=(status:number,body:unknown)=>new Response(JSON.stringify(body),{status,headers:{"Content-Type":"application/json"}});
function stubFetch(handler:(url:URL,init:RequestInit)=>Response|Promise<Response>){
  const calls:{url:URL;init:RequestInit}[]=[];
  globalThis.fetch=(async(url:URL|string,init:RequestInit={})=>{const u=new URL(String(url));calls.push({url:u,init});return handler(u,init);}) as typeof fetch;
  return calls;
}

test("detail como texto → mensaje y tipo por código HTTP",async()=>{
  const e=await toApiError(json(403,{detail:"No tienes permisos para esta operación"}));
  assert.equal(e.kind,"forbidden");assert.equal(e.status,403);assert.equal(e.message,"No tienes permisos para esta operación");
});
test("detail como objeto {code,message} (errores I3)",async()=>{
  const e=await toApiError(json(409,{detail:{code:"version_conflict",message:"El documento cambió",current_version:4}}));
  assert.equal(e.kind,"conflict");assert.equal(e.code,"version_conflict");assert.equal(e.extra.current_version,4);
});
test("422 de validación (lista de pydantic) se resume",async()=>{
  const e=await toApiError(json(422,{detail:[{loc:["body","title"],msg:"Field required"}]}));
  assert.equal(e.kind,"validation");assert.match(e.message,/title: Field required/);
});
test("503 auth_not_configured explica cómo activar la identidad de demostración",async()=>{
  const e=await toApiError(json(503,{detail:{code:"auth_not_configured",message:"x"}}));
  assert.equal(e.kind,"unavailable");assert.match(e.message,/PACHAADAPT_I3_DEV_AUTH=1/);
});
test("cuerpo vacío o no JSON usa el mensaje genérico en español",async()=>{
  const e=await toApiError(new Response("<html>",{status:501}));
  assert.equal(e.kind,"not_implemented");assert.match(e.message,/OCR/);
  assert.equal((await toApiError(new Response("",{status:404}))).kind,"not_found");
});
test("request envía identidad y JSON; arma la query sin valores vacíos",async()=>{
  setActor("demo-teacher","teacher");
  const calls=stubFetch(()=>json(200,{ok:true}));
  await request("/api/v1/x",{method:"PUT",body:{a:1},query:{expected_version:3,vacio:"",nada:undefined}});
  const {url,init}=calls[0];const h=init.headers as Record<string,string>;
  assert.equal(url.pathname,"/api/v1/x");assert.equal(url.search,"?expected_version=3");
  assert.equal(h["X-User-Id"],"demo-teacher");assert.equal(h["X-Role"],"teacher");assert.equal(h["Content-Type"],"application/json");
  assert.equal(init.body,JSON.stringify({a:1}));
});
test("subida multipart no fija Content-Type (lo calcula el navegador)",async()=>{
  const calls=stubFetch(()=>json(201,{}));
  await request("/api/v1/materials",{method:"POST",form:new FormData()});
  assert.equal((calls[0].init.headers as Record<string,string>)["Content-Type"],undefined);
});
test("fallo de red → ApiError kind network",async()=>{
  globalThis.fetch=(async()=>{throw new TypeError("fetch failed");}) as typeof fetch;
  await assert.rejects(()=>request("/x"),(e:ApiError)=>e.kind==="network"&&/No se pudo contactar/.test(e.message));
});
test("respuesta no exitosa lanza ApiError y raw devuelve texto",async()=>{
  stubFetch(()=>json(404,{detail:"Material no encontrado"}));
  await assert.rejects(()=>request("/x"),(e:ApiError)=>e instanceof ApiError&&e.kind==="not_found");
  stubFetch(()=>new Response("# Informe",{status:200}));
  assert.equal(await request<string>("/x",{raw:true}),"# Informe");
});
test("patrón de usuario coincide con el del backend",()=>{
  for(const ok of ["demo-student","a.b@c_d-1"])assert.ok(ID_PATTERN.test(ok));
  for(const bad of ["","con espacio","x".repeat(65),"a/b"])assert.ok(!ID_PATTERN.test(bad));
});

test("500/502/504 sin cuerpo (proxy de Vite sin backend) se tratan como fallo de red",async()=>{
  for(const status of [500,502,504]){
    const e=await toApiError(new Response("",{status}));
    assert.equal(e.kind,"network");assert.match(e.message,/start_server\.py/);
  }
  // un error real del backend (con cuerpo) NO se confunde con "backend apagado"
  assert.equal((await toApiError(new Response("Internal Server Error",{status:500}))).kind,"server");
});
