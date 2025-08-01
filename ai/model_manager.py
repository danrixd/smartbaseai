"""Utility for selecting models based on tenant configuration."""

from config.tenant_config import TenantConfig
from .models import OpenAIModel, LocalLLAMAModel, AnthropicModel


class ModelManager:
    """Instantiate models according to tenant configuration."""

    MODEL_MAP = {
        "openai": OpenAIModel,
        "local-llama": LocalLLAMAModel,
        "anthropic": AnthropicModel,
    }

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        config = TenantConfig.get(tenant_id)
        model_name = config.get("model", "openai")
        model_cls = self.MODEL_MAP.get(model_name)
        if model_cls is None:
            raise ValueError(f"Unsupported model: {model_name}")
        self.model = model_cls(**config.get("model_config", {}))

    def generate(self, prompt: str, **kwargs) -> str:
        """Delegate text generation to the underlying model."""
        return self.model.generate(prompt, **kwargs)
