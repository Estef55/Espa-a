import {localDB} from "./local-db";
import * as core from "../lib/materialsOffline";
import type {Detail,Fetchers} from "../lib/materialsOffline";
import type {MaterialInfo} from "../lib/materials.types";

// Enlaza la lógica de copia local con IndexedDB (almacenes "cache" y "assets" ya existentes; no cambia el esquema).
const kv:core.KV=localDB;
export const cacheMaterialList=(user:string,list:MaterialInfo[])=>core.saveList(kv,user,list);
export const getCachedMaterialList=(user:string)=>core.loadList(kv,user);
export const cacheMaterialDetail=(user:string,d:Detail)=>core.saveDetail(kv,user,d);
export const getCachedMaterialDetail=(user:string,id:string)=>core.loadDetail(kv,user,id);
export const getCachedOriginal=(user:string,id:string)=>core.loadOriginal(kv,user,id);
export const downloadMaterialForOffline=(user:string,id:string,f:Fetchers)=>core.downloadForOffline(kv,user,id,f);
export const materialOfflineState=(user:string,id:string)=>core.offlineState(kv,user,id);
export const saveAnswerDraft=(user:string,assignmentId:string,text:string)=>core.saveDraft(kv,user,assignmentId,text);
export const loadAnswerDraft=(user:string,assignmentId:string)=>core.loadDraft(kv,user,assignmentId);
