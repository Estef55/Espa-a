// Estado y descarga de cambios del servidor (backend: /api/v1/synchronization). El envío (push) vive en offline/sync-queue.ts.
import { request } from "./http.ts";
import type { SyncPull, SyncServerStatus } from "../lib/types.ts";

export const getServerSyncStatus = () => request<SyncServerStatus>("/api/v1/synchronization/status");
export const pullChanges = (since?: string) => request<SyncPull>("/api/v1/synchronization/pull", { query: { since } });
