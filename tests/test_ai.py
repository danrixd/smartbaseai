import pytest

from ai.model_manager import ModelManager
from ai.models import OpenAIModel, LocalLLAMAModel, AnthropicModel, OllamaModel
from chatbot.response_generator import ResponseGenerator
from config import tenant_config


def test_default_model_is_openai(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "t1", {})
    manager = ModelManager("t1")
    assert isinstance(manager.model, OpenAIModel)
    assert manager.generate("hi") == "[OpenAI] Response to: hi"


def test_select_specific_model(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "t2", {"model": "local-llama"})
    manager = ModelManager("t2")
    assert isinstance(manager.model, LocalLLAMAModel)
    assert manager.generate("hey") == "[LLaMA] Response to: hey"

    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "t3", {"model": "anthropic"})
    manager = ModelManager("t3")
    assert isinstance(manager.model, AnthropicModel)
    assert manager.generate("yo") == "[Anthropic] Response to: yo"

    # using ollama should not raise even if server isn't running
    monkeypatch.setitem(
        tenant_config.TENANT_CONFIGS,
        "t4",
        {"model": "ollama", "model_config": {"model_name": "llama3"}},
    )
    manager = ModelManager("t4")
    assert isinstance(manager.model, OllamaModel)
    assert manager.generate("sup").startswith("[Ollama]")


def test_invalid_model(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "bad", {"model": "unknown"})
    with pytest.raises(ValueError):
        ModelManager("bad")



def test_response_generator_with_history(monkeypatch):
    class DummyResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "ok"}

    monkeypatch.setattr(__import__("requests"), "post", lambda *a, **k: DummyResp())

    gen = ResponseGenerator("t1")
    gen.rag.store.add_document("d1", "info", {"source": "test"})

    reply = gen.generate_response("info?", [{"role": "user", "text": "hi"}])
    assert reply == "ok"
