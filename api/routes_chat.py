from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from chatbot.conversation_manager import ConversationManager
from chatbot.response_generator import ResponseGenerator
from tenants.tenant_manager import TenantManager

from .auth import get_current_user


router = APIRouter(prefix="/chat", tags=["chat"])
conversation_manager = ConversationManager()
tenant_manager = TenantManager()


class ChatRequest(BaseModel):
    session_id: str
    tenant_id: str
    message: str


@router.post("/message")
def chat_message(req: ChatRequest, user: dict = Depends(get_current_user)):
    """Receive a chat message and return a generated reply."""
    # Load tenant configuration to determine which model to use
    tenant_config = tenant_manager.get(req.tenant_id)
    if tenant_config is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    model_type = tenant_config.get("model_type", "ollama")
    model_name = tenant_config.get("model_name", "llama3.2")

    conversation_manager.start_session(req.session_id)
    conversation_manager.add_message(req.session_id, "user", req.message)
    history = conversation_manager.history(req.session_id)

    generator = ResponseGenerator(
        tenant_id=req.tenant_id,
        model_type=model_type,
        model_name=model_name,
    )
    reply = generator.generate_response(req.message, history)

    conversation_manager.add_message(req.session_id, "assistant", reply)
    return {
        "reply": reply,
        "history": conversation_manager.history(req.session_id),
    }
