// Asistente de IA para docentes (backend: /api/v1/ai-chat, solo docente).
import { request } from "./http.ts";
import type { AiStatus, ChatReply, Conversation } from "../lib/types.ts";

export const MAX_QUESTION = 4000; // mismo límite que ai/assistant/chat_service.py
export const getAiStatus = () => request<AiStatus>("/api/v1/ai-chat/status");
export const sendChat = (question: string, conversationId?: string | null, documentId?: string | null) =>
  request<ChatReply>("/api/v1/ai-chat", {
    method: "POST", timeoutMs: 90000,
    body: { question, ...(conversationId ? { conversation_id: conversationId } : {}), ...(documentId ? { document_id: documentId } : {}) },
  });
export const getConversation = (id: string) => request<Conversation>(`/api/v1/ai-chat/conversations/${encodeURIComponent(id)}`);
