import type {AdaptationKind,QuizQuestion} from "./types.ts";
export const ADAPTATION_LABEL:Record<AdaptationKind,string>={summary:"Resumen",easy_read:"Lectura fácil",quiz:"Preguntas de comprensión",outline:"Esquema del contenido",image_notes:"Notas de imágenes",audio:"Audio"};
/** Texto plano del resultado de una adaptación, para copiarlo o guardarlo como documento editable. */
export function adaptationToText(result:string|QuizQuestion[]):string{
  if(typeof result==="string")return result;
  return result.map(q=>`${q.id}. ${q.question}`).join("\n\n");
}
