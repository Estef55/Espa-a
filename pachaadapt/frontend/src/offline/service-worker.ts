/// <reference lib="webworker" />
const sw=self as unknown as ServiceWorkerGlobalScope;
const CACHE="pachaadapt-shell-v1";
const SHELL=["/","/offline.html","/manifest.json"];
sw.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>sw.skipWaiting())));
sw.addEventListener("activate",event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>sw.clients.claim())));
sw.addEventListener("fetch",event=>{
  const req=event.request;
  if(req.method!=="GET" || new URL(req.url).origin!==sw.location.origin)return;
  event.respondWith(fetch(req).then(response=>{
    if(response.ok){const copy=response.clone();void caches.open(CACHE).then(c=>c.put(req,copy));}
    return response;
  }).catch(async()=> (await caches.match(req)) ?? (await caches.match("/offline.html"))!));
});
