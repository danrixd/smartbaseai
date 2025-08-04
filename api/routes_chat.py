from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from chatbot.conversation_manager import ConversationManager
from chatbot.response_generator import ResponseGenerator
from tenants.tenant_manager import TenantManager
import logging

from db import conversation_repository, audit_log_repository
from .auth_middleware import get_current_user


router = APIRouter(prefix="/chat", tags=["chat"])
conversation_manager = ConversationManager()
tenant_manager = TenantManager()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    session_id: str
    tenant_id: str
    message: str


@router.post("/message")
def chat_message(req: ChatRequest, user=Depends(get_current_user)):
    """Receive a chat message and return a generated reply."""
    # Load tenant configuration to determine which model to use
    tenant_id = req.tenant_id.strip()
    if user.get("role") != "super_admin" and user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant access denied")

    tenant_config = tenant_manager.get(tenant_id)
    if tenant_config is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    model_type = tenant_config.get("model_type", "ollama")
    model_name = tenant_config.get("model_name", "llama3.2")

    conversation_manager.start_session(req.session_id)
    conversation_manager.add_message(req.session_id, "user", req.message)
    conversation_repository.add_message(
        req.session_id, user["username"], tenant_id, "user", req.message
    )
    history = conversation_manager.history(req.session_id)

    generator = ResponseGenerator(
        tenant_id=tenant_id,
        model_type=model_type,
        model_name=model_name,
    )
    reply = generator.generate_response(req.message, history)
    if model_type == "ollama" and not reply.startswith("[Ollama"):
        reply = f"[Ollama] {reply}"

    conversation_manager.add_message(req.session_id, "assistant", reply)
    conversation_repository.add_message(
        req.session_id, user["username"], tenant_id, "assistant", reply
    )
    audit_log_repository.log_action(user["username"], "chat_message", req.session_id)
    return {
        "reply": reply,
        "history": conversation_repository.get_history(
            req.session_id, user["username"]
        ),
    }


@router.get("/history")
def chat_history(session_id: str, user=Depends(get_current_user)):
    """Return chat history for a session."""
    return {"history": conversation_repository.get_history(session_id, user["username"])}


@router.get("/sessions")
def chat_sessions(user=Depends(get_current_user)):
    """Return a list of chat sessions for the current user."""
    return {"sessions": conversation_repository.list_sessions(user["username"])}


@router.delete("/session/{session_id}")
def delete_chat_session(session_id: str, user=Depends(get_current_user)):
    """Delete a chat session and its history."""
    conversation_repository.delete_session(session_id, user["username"])
    audit_log_repository.log_action(user["username"], "delete_session", session_id)
    return {"status": "deleted"}
