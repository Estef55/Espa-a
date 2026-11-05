// Asistente de IA para docentes (backend: /api/v1/ai-chat, solo docente).
import { request } from "./http.ts";
import { createDocument } from "./documents.service.ts";
import type { AiStatus, ChatReply, Conversation, DocumentFull } from "../lib/types.ts";

export const MAX_QUESTION = 4000; // mismo límite que ai/assistant/chat_service.py
export const getAiStatus = () => request<AiStatus>("/api/v1/ai-chat/status");
export const sendChat = (question: string, conversationId?: string | null, documentId?: string | null) =>
  request<ChatReply>("/api/v1/ai-chat", {
    method: "POST", timeoutMs: 90000,
    body: { question, ...(conversationId ? { conversation_id: conversationId } : {}), ...(documentId ? { document_id: documentId } : {}) },
  });
export const getConversation = (id: string) => request<Conversation>(`/api/v1/ai-chat/conversations/${encodeURIComponent(id)}`);
/** Persiste una propuesta SOLO después de que el docente la haya revisado/editado en la interfaz. */
export const saveAssistantProposal = (title: string, content: string): Promise<DocumentFull> =>
  createDocument({ title, content });
