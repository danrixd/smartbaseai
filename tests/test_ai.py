import pytest

from ai.model_manager import ModelManager
from ai.models import OpenAIModel, LocalLLAMAModel, AnthropicModel
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


def test_invalid_model(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, "bad", {"model": "unknown"})
    with pytest.raises(ValueError):
        ModelManager("bad")
