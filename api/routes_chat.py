from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from chatbot.conversation_manager import ConversationManager
from chatbot.response_generator import ResponseGenerator

from .auth import get_current_user


router = APIRouter(prefix="/chat", tags=["chat"])
conversation_manager = ConversationManager()


class ChatRequest(BaseModel):
    session_id: str
    tenant_id: str
    message: str


@router.post("/message")
def chat_message(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Receive a chat message and return a generated reply."""
    conversation_manager.start_session(req.session_id)
    conversation_manager.add_message(req.session_id, "user", req.message)
    history = conversation_manager.history(req.session_id)
    generator = ResponseGenerator(req.tenant_id)
    reply = generator.generate(req.message, history)
    conversation_manager.add_message(req.session_id, "assistant", reply)
    return {"reply": reply, "history": conversation_manager.history(req.session_id)}
