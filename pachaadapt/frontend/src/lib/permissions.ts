// Matriz de permisos derivada del backend (identity.require_teacher y security.require_roles).
import type {Role} from "./types";
export type Feature="assignments.write"|"submissions.send"|"submissions.review"|"library.write"|"materials.upload"|"documents"|"preferences"|"chat"|"reports";
const ALLOWED:Record<Feature,Role[]>={
  "assignments.write":["teacher","admin"],"submissions.send":["student"],"submissions.review":["teacher","admin"],
  "library.write":["teacher","admin"],"materials.upload":["teacher"],documents:["teacher"],preferences:["teacher"],chat:["teacher"],reports:["teacher"],
};
export const can=(role:Role,feature:Feature)=>ALLOWED[feature].includes(role);
const ROLE_NAME:Record<Role,string>={student:"Estudiante",teacher:"Docente",admin:"Administrador"};
export function denialMessage(role:Role,feature:Feature):string{
  const who=ALLOWED[feature].map(r=>ROLE_NAME[r].toLowerCase()).join(" o ");
  return `Esta función es solo para el perfil ${who}. Tu perfil actual es ${ROLE_NAME[role].toLowerCase()}. Cámbialo en la sección Perfil.`;
}
