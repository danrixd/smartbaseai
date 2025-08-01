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
            for key, value in model_config.items():
                if key != "model_name":
                    final_cfg[key] = value
        self.model = model_cls(**final_cfg)

    def generate(self, prompt: str, **kwargs) -> str:
        """Delegate text generation to the underlying model."""
        return self.model.generate(prompt, **kwargs)
