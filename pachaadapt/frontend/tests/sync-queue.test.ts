import test from "node:test";
import assert from "node:assert/strict";

test("rechazos definitivos se conservan sin reintento automático y admiten reintento explícito", async () => {
  const rows = new Map<string, any>();
  const request = (result: any, tx: any) => {
    const req: any = {};
    queueMicrotask(() => { req.result = result; req.onsuccess?.(); tx.oncomplete?.(); });
    return req;
  };
  const store = {
    put: (value: any, tx: any) => { rows.set(value.operation_id, value); return request(value.operation_id, tx); },
    delete: (key: string, tx: any) => { rows.delete(key); return request(undefined, tx); },
    getAll: (tx: any) => request([...rows.values()], tx),
  };
  const db = { objectStoreNames: { contains: () => true }, close: () => undefined, transaction: (_name: string, _mode: string) => {
    const tx: any = { oncomplete: undefined, onerror: undefined, objectStore: () => ({
      put: (v: any) => store.put(v, tx), delete: (k: string) => store.delete(k, tx), getAll: () => store.getAll(tx),
    }) };
    return tx;
  } };
  Object.defineProperty(globalThis, "indexedDB", { configurable: true, value: { open: () => {
    const req: any = {};
    queueMicrotask(() => { req.result = db; req.onsuccess?.(); });
    return req;
  } } });
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: { onLine: true } });
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (key: string) => key === "pacha-user" ? "student-a" : "student",
    setItem: () => undefined,
  } });
  Object.defineProperty(globalThis, "window", { configurable: true, value: { dispatchEvent() {}, addEventListener() {} } });
  let calls = 0;
  globalThis.fetch = async () => {
    calls += 1;
    return calls === 1
      ? new Response(JSON.stringify({ results: [{ status: "rejected", reason: "assignment_unavailable" }] }), { status: 200 })
      : new Response(JSON.stringify({ results: [{ status: "acknowledged" }] }), { status: 200 });
  };

  const { localDB } = await import("../src/offline/local-db.ts");
  const { synchronize, retryRejected } = await import("../src/offline/sync-queue.ts");
  const op = { operation_id: crypto.randomUUID(), entity_type: "submission" as const,
    entity_id: "assignment-a", payload: { assignment_id: "assignment-a", answer: "mi respuesta", base_version: 0,
      client_updated_at: new Date().toISOString() }, created_at: new Date().toISOString(), attempts: 0,
    actor: { id: "student-a", role: "student" } };
  await localDB.enqueue(op);

  await synchronize();
  const rejected = (await localDB.all())[0];
  assert.equal(rejected.rejection?.reason, "assignment_unavailable");
  assert.equal(calls, 1);

  await synchronize();
  assert.equal(calls, 1, "un rechazo definitivo no debe reintentarse en automático");

  await retryRejected(op.operation_id);
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(calls, 2, "el usuario puede volver a intentar explícitamente");
  assert.equal((await localDB.all()).length, 0, "la respuesta sale de la cola solo tras ACK");
});
