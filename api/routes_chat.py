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
    model_provider: str | None = None
    model_name: str | None = None


def _resolve_model(tenant_config: dict, req: ChatRequest) -> tuple[str, str]:
    """Pick the (provider, model_name) for this request.

    Priority: explicit request override → tenant's ``models[0]`` default →
    legacy ``model_type``/``model_name`` fallback → ollama/llama3.
    """
    if req.model_provider:
        return req.model_provider, req.model_name or ""
    models = tenant_config.get("models") or []
    if models:
        first = models[0]
        return first.get("provider", "ollama"), first.get("name") or first.get("model_name", "")
    return (
        tenant_config.get("model_type", "ollama"),
        tenant_config.get("model_name", "llama3.2"),
    )


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

    model_type, model_name = _resolve_model(tenant_config, req)

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


@router.post("/trace")
def chat_trace(req: ChatRequest, user=Depends(get_current_user)):
    """Run a chat query and return the full pipeline trace for visualization.

    This endpoint is intentionally read-only with respect to the conversation
    store — it does not append to history or write audit logs — so the RAG
    visualizer can run experimental queries without polluting real sessions.
    """
    tenant_id = req.tenant_id.strip()
    if user.get("role") != "super_admin" and user.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant access denied")

    tenant_config = tenant_manager.get(tenant_id)
    if tenant_config is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    model_type, model_name = _resolve_model(tenant_config, req)

    history = conversation_manager.history(req.session_id)
    generator = ResponseGenerator(
        tenant_id=tenant_id,
        model_type=model_type,
        model_name=model_name,
    )
    return generator.generate_response_trace(req.message, history)


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
