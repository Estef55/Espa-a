import {useCallback,useEffect,useRef,useState} from "react";
import {loadAnswerDraft,saveAnswerDraft} from "../offline/materials-cache";

/** Borrador de respuesta guardado en este dispositivo: no se pierde si se cae la conexión o se cierra la pestaña. */
export function useAnswerDraft(user:string,assignmentId:string){
  const [text,setTextState]=useState("");const [restored,setRestored]=useState(false);const [saveError,setSaveError]=useState(false);
  const timer=useRef<ReturnType<typeof setTimeout>>(undefined);const latest=useRef("");
  useEffect(()=>{let alive=true;
    loadAnswerDraft(user,assignmentId).then(t=>{if(alive&&t&&!latest.current){latest.current=t;setTextState(t);setRestored(true);}}).catch(()=>undefined);
    return()=>{alive=false;clearTimeout(timer.current);};
  },[user,assignmentId]);
  const persist=(value:string)=>saveAnswerDraft(user,assignmentId,value).then(()=>setSaveError(false)).catch(()=>setSaveError(true));
  const setText=useCallback((value:string)=>{
    latest.current=value;setTextState(value);setRestored(false);clearTimeout(timer.current);
    timer.current=setTimeout(()=>void persist(value),400);
  },[user,assignmentId]);// eslint-disable-line react-hooks/exhaustive-deps
  const clear=useCallback(()=>{clearTimeout(timer.current);latest.current="";setTextState("");setRestored(false);void persist("");},[user,assignmentId]);// eslint-disable-line react-hooks/exhaustive-deps
  return {text,setText,clear,restored,saveError};
}
