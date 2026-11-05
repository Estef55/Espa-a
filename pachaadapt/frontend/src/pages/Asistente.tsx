import {useEffect,useRef,useState} from "react";
import {useApp} from "../context";
import {useAsync} from "../hooks/useAsync";
import {getConversation,MAX_QUESTION,saveAssistantProposal,sendChat} from "../services/ai.service";
import {listDocuments} from "../services/documents.service";
import type {ChatMessage,ChatReply} from "../lib/types";
import {ErrorNotice,Field,Gate,Loading,Notice,NotConnected,OfflineNotice,PageHeader,Panel} from "../components/ui";

function Inner(){
  const {profile,ai,refreshAi,online}=useApp();
  const convKey=`pacha-chat:${profile.user}`;
  const [convId,setConvId]=useState<string|null>(()=>localStorage.getItem(convKey));
  const [messages,setMessages]=useState<ChatMessage[]>([]);const [reply,setReply]=useState<ChatReply|null>(null);
  const [question,setQuestion]=useState("");const [docId,setDocId]=useState("");
  const [proposalTitle,setProposalTitle]=useState("Propuesta del asistente");const [proposal,setProposal]=useState("");
  const [savingDocument,setSavingDocument]=useState(false);const [savedTitle,setSavedTitle]=useState("");const [documentError,setDocumentError]=useState<Error|null>(null);
  const [sending,setSending]=useState(false);const [error,setError]=useState<Error|null>(null);const [info,setInfo]=useState("");
  const docs=useAsync(()=>listDocuments(false),[profile.user]);
  const log=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    if(!convId)return;
    getConversation(convId).then(c=>{
      const history=c.messages.filter(m=>m.role!=="system");setMessages(history);setDocId(c.document_id??"");
      setProposal([...history].reverse().find(m=>m.role==="assistant")?.content??"");
    })
      .catch((e:{kind?:string})=>{if(e.kind==="not_found"){localStorage.removeItem(convKey);setConvId(null);setInfo("La conversación guardada ya no existe; puedes empezar una nueva.");}});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);
  useEffect(()=>{log.current?.scrollTo({top:log.current.scrollHeight});},[messages]);
  const configured=!!ai.data?.ai_provider_configured;
  const tooLong=question.length>MAX_QUESTION;

  async function send(e:React.FormEvent){
    e.preventDefault();const q=question.trim();
    if(!q||tooLong)return;
    setSending(true);setError(null);setInfo("");
    try{
      const r=await sendChat(q,convId,docId||null);
      setConvId(r.conversation_id);localStorage.setItem(convKey,r.conversation_id);setReply(r);setProposal(r.answer);setSavedTitle("");setDocumentError(null);
      setMessages(m=>[...m,{role:"user",content:q},{role:"assistant",content:r.answer}]);setQuestion("");
    }catch(err){setError(err instanceof Error?err:new Error(String(err)));}finally{setSending(false);}
  }
  async function saveProposal(){
    if(!proposal.trim())return;
    setSavingDocument(true);setDocumentError(null);setInfo("");
    try{const doc=await saveAssistantProposal(proposalTitle.trim()||"Propuesta del asistente",proposal);setSavedTitle(doc.title);setInfo("Propuesta guardada como documento editable después de tu revisión.");docs.reload();}
    catch(err){setDocumentError(err instanceof Error?err:new Error(String(err)));}finally{setSavingDocument(false);}
  }
  function restart(){localStorage.removeItem(convKey);setConvId(null);setMessages([]);setReply(null);setDocId("");setProposal("");setSavedTitle("");setDocumentError(null);setError(null);setInfo("");}

  return <>
    <OfflineNotice what="El asistente"/>
    {ai.loading&&!ai.data?<Loading label="Comprobando el estado del asistente…"/>:ai.error?<ErrorNotice error={ai.error} onRetry={refreshAi}/>:!configured&&
      <NotConnected>No hay un proveedor de IA configurado en el servidor, por eso el asistente está desactivado y no se generan respuestas de ejemplo. Para desarrollo local, copia <code>.env.example</code> como <code>.env</code>, configura el proveedor, modelo y clave solo en ese archivo del backend, y reinicia el servidor. No pegues la API key aquí ni en el frontend. Consulta <code>CONFIGURACION_SERVICIOS_IA.md</code>. <button className="btn btn-quiet" onClick={refreshAi}>Volver a comprobar</button></NotConnected>}
    {info&&<Notice kind="info">{info}</Notice>}
    <div className="split chat">
      <Panel title="Conversación" actions={<button className="btn btn-quiet" onClick={restart} disabled={sending||(!convId&&!messages.length)}>Nueva conversación</button>}>
        <div className="chat-log" ref={log} role="log" aria-live="polite" aria-label="Mensajes de la conversación" tabIndex={0}>
          {!messages.length&&!sending&&<p className="hint">Escribe una pregunta sobre tu material o un documento. Las respuestas las genera un modelo de IA y pueden contener errores.</p>}
          {messages.map((m,i)=><div className={`msg ${m.role}`} key={i}><span className="msg-who">{m.role==="user"?"Tú":"Asistente de IA"}</span><p className="prewrap">{m.content}</p></div>)}
          {sending&&<p className="loading" role="status"><span className="spinner" aria-hidden="true"/>El asistente está respondiendo…</p>}
        </div>
        {reply&&<div className="meta"><span>Generado por IA ({reply.provider} · {reply.model}).</span>{reply.document_context&&<span>Contexto: «{reply.document_context.title}», versión {reply.document_context.version}{reply.document_context.truncated?" (texto recortado por su longitud)":""}.</span>}</div>}
        {reply&&<p className="hint">{reply.notice}</p>}
        {proposal&&<section className="result" aria-labelledby="proposal-heading">
          <h3 id="proposal-heading">Propuesta revisable</h3>
          <p className="hint">Revisa y edita el contenido antes de guardarlo. Nada se añade a Documentos hasta que pulses el botón.</p>
          <Field label="Título del documento"><input value={proposalTitle} onChange={e=>{setProposalTitle(e.target.value);setSavedTitle("");setInfo("");}} maxLength={200}/></Field>
          <Field label="Contenido editable"><textarea rows={10} value={proposal} onChange={e=>{setProposal(e.target.value);setSavedTitle("");setInfo("");}}/></Field>
          <div className="row"><button type="button" className="btn btn-primary" onClick={()=>void saveProposal()} disabled={!online||savingDocument||!proposal.trim()}>{savingDocument?"Guardando…":"Guardar como documento"}</button>{savedTitle&&<a className="btn btn-quiet" href="#/documentos">Abrir «{savedTitle}» en Documentos</a>}</div>
          {documentError&&<ErrorNotice error={documentError}/>}
        </section>}
        <form className="form" onSubmit={e=>void send(e)}>
          <Field label="Tu pregunta" hint={`${question.length} / ${MAX_QUESTION} caracteres`}><textarea rows={4} value={question} onChange={e=>setQuestion(e.target.value)} disabled={!configured||sending} aria-invalid={tooLong}/></Field>
          {tooLong&&<Notice kind="error">La pregunta supera los {MAX_QUESTION} caracteres.</Notice>}
          {error&&<ErrorNotice error={error}/>}
          <div><button className="btn btn-primary" disabled={!configured||sending||!online||!question.trim()||tooLong}>{sending?"Enviando…":"Enviar pregunta"}</button></div>
        </form>
      </Panel>
      <Panel title="Documento de contexto" description="Opcional. El asistente lee la versión actual del documento y distingue lo que dice de lo que sugiere.">
        {docs.loading&&!docs.data?<Loading/>:docs.error?<ErrorNotice error={docs.error} onRetry={docs.reload}/>:
        <Field label="Documento" hint={convId?"Queda asociado a esta conversación; empieza una nueva para cambiarlo.":(docs.data?.length?"":"Aún no tienes documentos; créalos en «Documentos editables».")}>
          <select value={docId} onChange={e=>setDocId(e.target.value)} disabled={!!convId||!configured}><option value="">Sin documento</option>{(docs.data??[]).map(d=><option key={d.id} value={d.id}>{d.title} (v{d.current_version})</option>)}</select></Field>}
        <p className="hint">El asistente aplica tus <a href="#/preferencias">preferencias</a> (nivel, tono, extensión, idioma).</p>
      </Panel>
    </div>
  </>;
}
export default function Asistente(){
  return <><PageHeader title="Asistente de IA" description="Consulta a un modelo de IA sobre tus materiales. No inventa datos: sin proveedor configurado, no responde."/><Gate feature="chat"><Inner/></Gate></>;
}
