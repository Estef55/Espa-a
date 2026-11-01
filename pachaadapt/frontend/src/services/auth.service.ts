// IDENTIDAD DE DEMOSTRACIÓN. El proyecto no tiene autenticación real (backend/app/api/v1/auth.py es TODO):
// el backend acepta las cabeceras X-User-Id / X-Role solo si PACHAADAPT_I3_DEV_AUTH=1. Nada de esto es seguro para producción.
import { ID_PATTERN, request } from "./http.ts";
import type { Health, Role } from "../lib/types.ts";

// Se conserva la asignación original del selector: el administrador de demostración usa el usuario demo-teacher.
export const DEMO_USERS: Record<Role, string> = { student: "demo-student", teacher: "demo-teacher", admin: "demo-teacher" };
export const ROLE_LABEL: Record<Role, string> = { student: "Estudiante", teacher: "Docente", admin: "Administrador" };
export type Profile = { role: Role; user: string };
type KV = Pick<Storage, "getItem" | "setItem">;

export function isValidUserId(value: string) { return ID_PATTERN.test(value); }
export function loadProfile(storage: KV | undefined = globalThis.localStorage): Profile {
  const role = storage?.getItem("pacha-role");
  const safeRole: Role = role === "teacher" || role === "admin" ? role : "student";
  const user = storage?.getItem("pacha-user") ?? "";
  return { role: safeRole, user: isValidUserId(user) ? user : DEMO_USERS[safeRole] };
}
export function saveProfile(profile: Profile, storage: KV | undefined = globalThis.localStorage) {
  storage?.setItem("pacha-role", profile.role); storage?.setItem("pacha-user", profile.user);
}
export const getHealth = () => request<Health>("/health", { timeoutMs: 8000 });
