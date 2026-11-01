"""Endpoints del chat de IA para docentes. Prefijo: /api/v1/ai-chat."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1._deps import principal, run
from app.core.identity import Principal
from app.services.container import get_container

router = APIRouter(prefix="/api/v1/ai-chat", tags=["ai-chat"])


class ChatIn(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None


@router.get("/status")
def status(p: Principal = Depends(principal)):
    c = get_container()
    return {"ai_provider_configured": c.assistant.provider_configured,
            "document_processor_connected": c.documents.processor is not None,
            "learning_data_source_connected": c.reports.data_source is not None}


@router.post("")
def chat(body: ChatIn, p: Principal = Depends(principal)):
    return run(get_container().assistant.chat, p.user_id, body.question, body.conversation_id, body.document_id)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, p: Principal = Depends(principal)):
    return run(get_container().assistant.get_conversation, p.user_id, conversation_id)
