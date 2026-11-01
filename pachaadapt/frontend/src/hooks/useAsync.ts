import {useCallback,useEffect,useRef,useState} from "react";

export type AsyncState<T>={data?:T;error?:Error;loading:boolean;reload:()=>void;setData:(value:T)=>void};
/** Carga asíncrona con cancelación de respuestas obsoletas. Vuelve a cargar cuando cambian `deps`. */
export function useAsync<T>(load:()=>Promise<T>,deps:unknown[]):AsyncState<T>{
  const [state,setState]=useState<{data?:T;error?:Error;loading:boolean}>({loading:true});
  const [tick,setTick]=useState(0);
  const run=useRef(0);
  useEffect(()=>{
    const id=++run.current;
    setState(s=>({data:s.data,loading:true}));
    load().then(data=>{if(id===run.current)setState({data,loading:false});})
      .catch((error:unknown)=>{if(id===run.current)setState({error:error instanceof Error?error:new Error(String(error)),loading:false});});
    return ()=>{run.current++;};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[tick,...deps]);
  const reload=useCallback(()=>setTick(t=>t+1),[]);
  const setData=useCallback((value:T)=>setState({data:value,loading:false}),[]);
  return {...state,reload,setData};
}
