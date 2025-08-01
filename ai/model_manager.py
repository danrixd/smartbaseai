"""Utility for selecting models based on tenant configuration."""

from config.tenant_config import TenantConfig
from .models import (
    OpenAIModel,
    LocalLLAMAModel,
    AnthropicModel,
    OllamaModel,
)


class ModelManager:
    """Instantiate models according to tenant configuration."""

    MODEL_MAP = {
        "openai": OpenAIModel,
        "local-llama": LocalLLAMAModel,
        "anthropic": AnthropicModel,
        "ollama": OllamaModel,
    }

    def __init__(
        self,
        tenant_id: str,
        model_type: str | None = None,
        model_config: dict | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        config = TenantConfig.get(tenant_id)
        name = model_type or config.get("model", "openai")
        model_cls = self.MODEL_MAP.get(name)
        if model_cls is None:
            raise ValueError(f"Unsupported model: {name}")
        final_cfg = dict(config.get("model_config", {}))
        if model_config:
            final_cfg.update(model_config)
        if name != "ollama":
            final_cfg.pop("model_name", None)
        self.model = model_cls(**final_cfg)

    def generate(self, prompt: str, **kwargs) -> str:
        """Delegate text generation to the underlying model."""
        return self.model.generate(prompt, **kwargs)
